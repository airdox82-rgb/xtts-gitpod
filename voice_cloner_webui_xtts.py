import os
import time
import tempfile
from pathlib import Path
from typing import Optional

import gradio as gr

# Audio I/O
import soundfile as sf

# Coqui TTS (XTTS v2)
from TTS.api import TTS

# -----------------------
# Globaler Zustand
# -----------------------
MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

_tts_model: Optional[TTS] = None
_ref_voice_path: Optional[str] = None
_last_out_path: Optional[str] = None

TMP_DIR = Path(tempfile.gettempdir()) / "voice_cloner_pro"
TMP_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------
# Helper
# -----------------------
def load_model(progress=gr.Progress(track_tqdm=True)):
    """Lazy-Load des XTTS v2 Modells (einmalig)."""
    global _tts_model
    if _tts_model is not None:
        return "✅ Modell bereits geladen."

    progress(0, desc="Lade XTTS v2 Modell … (einmalig, bitte warten)")
    try:
        _tts_model = TTS(MODEL_NAME)
        progress(1, desc="Fertig")
        return "✅ XTTS v2 erfolgreich geladen."
    except Exception as e:
        _tts_model = None
        return f"❌ Modell konnte nicht geladen werden: {e}"


def save_wav_stub(seconds=1.0, sr=22050) -> str:
    """Erstellt eine kurze Stille-WAV (Fallback/Debug)."""
    import numpy as np
    samples = int(seconds * sr)
    data = np.zeros((samples,), dtype="float32")
    out = TMP_DIR / f"silence_{int(time.time())}.wav"
    sf.write(out, data, sr)
    return str(out)


def remember_reference_voice(ref_wav_path: Optional[str]) -> str:
    """Speichert den Pfad zur Referenzstimme (aufgenommen/hochgeladen)."""
    global _ref_voice_path
    if not ref_wav_path:
        return "❌ Keine Datei erhalten."
    if not Path(ref_wav_path).exists():
        return "❌ Datei nicht gefunden."
    _ref_voice_path = ref_wav_path
    dur_info = ""
    try:
        info = sf.info(ref_wav_path)
        dur_info = f" ({info.duration:.1f}s, {info.samplerate} Hz)"
    except Exception:
        pass
    return f"✅ Referenzstimme gesetzt: {Path(ref_wav_path).name}{dur_info}"


def generate_tts(text: str, language: str, progress=gr.Progress(track_tqdm=True)):
    """Erzeugt TTS mit XTTS v2 und optionaler Referenzstimme (Zero-Shot Voice Cloning)."""
    global _tts_model, _ref_voice_path, _last_out_path

    if not text or text.strip() == "":
        return None, "❌ Bitte Text eingeben."

    # Modell laden (falls noch nicht geladen)
    if _tts_model is None:
        status = load_model(progress=progress)
        if _tts_model is None:
            return None, status

    # Ausgabedatei vorbereiten
    out_path = TMP_DIR / f"tts_{int(time.time())}.wav"

    # Coqui-XTTS Aufruf
    try:
        progress(0, desc="Erzeuge Audio …")
        kwargs = dict(text=text, language=language, file_path=str(out_path))

        # Zero-Shot Voice Cloning, wenn vorhanden
        if _ref_voice_path and Path(_ref_voice_path).exists():
            kwargs["speaker_wav"] = _ref_voice_path

        # XTTS v2: tts_to_file(text=..., speaker_wav=<path>, language="de", file_path="out.wav")
        _tts_model.tts_to_file(**kwargs)

        _last_out_path = str(out_path)
        progress(1, desc="Fertig")
        return str(out_path), f"✅ Audio generiert: {out_path.name}"
    except Exception as e:
        # Fallback: Stille-Datei, damit UI nicht bricht
        fallback = save_wav_stub(0.5)
        return fallback, f"❌ Fehler bei der Audioerzeugung: {e}"


def clear_ref():
    """Vergisst die Referenzstimme."""
    global _ref_voice_path
    _ref_voice_path = None
    return "ℹ️ Referenzstimme verworfen."


def get_download_path():
    """Gibt den letzten generierten Pfad zurück (für 'Datei speichern')."""
    global _last_out_path
    if _last_out_path and Path(_last_out_path).exists():
        return _last_out_path
    return None


# -----------------------
# UI (Gradio)
# -----------------------
THEME = gr.themes.Monochrome(
    primary_hue="slate",
    neutral_hue="slate",
    radius_size="lg",
).set(
    body_background_fill="#0b0f19",  # dunkler Hintergrund
    body_text_color="#e5e7eb",
    block_background_fill="#111827",
    input_background_fill="#0b0f19",
    button_secondary_background_fill="#1f2937",
)

with gr.Blocks(title="Voice Cloner Pro (XTTS v2)", theme=THEME, css="""
:root { --radius-lg: 16px; }
.gradio-container { max-width: 980px !important; margin: 0 auto; }
#brand h1 { letter-spacing: .5px; }
.footer-note { opacity:.8; font-size:.9rem; }
""") as demo:
    with gr.Column(elem_id="brand"):
        gr.Markdown(
            """
# 🎙️ Voice Cloner Pro
**Zero-Shot Voice Cloning & TTS** mit **Coqui XTTS v2** – direkt in Gitpod im Browser.  
> Aufnahme ➜ Referenzstimme setzen ➜ Text eingeben ➜ Audio generieren
""")

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 1) Referenzstimme (optional)")
            ref_audio = gr.Audio(
                sources=["microphone", "upload"],
                type="filepath",
                label="Aufnehmen oder WAV/MP3 hochladen (5–30s sprechen ist ideal)",
            )
            set_ref_btn = gr.Button("🎯 Referenzstimme setzen")
            clear_ref_btn = gr.Button("♻️ Referenzstimme verwerfen")
            ref_status = gr.Markdown("Noch keine Referenzstimme gesetzt.")

        with gr.Column():
            gr.Markdown("### 2) Text zu Sprache")
            lang = gr.Dropdown(
                label="Sprache",
                choices=["de", "en", "fr", "es", "it", "pt", "nl", "pl", "ru", "tr", "ja", "ko", "zh"],
                value="de",
            )
            text = gr.Textbox(
                label="Text",
                placeholder="Gib hier deinen Text ein …",
                lines=5,
            )
            gen_btn = gr.Button("🗣️ Audio generieren", variant="primary")

    with gr.Row():
        with gr.Column(scale=2):
             gr.Markdown("### Ergebnis")
             audio_out = gr.Audio(label="Wiedergabe", interactive=False)
             status = gr.Markdown()
        with gr.Column(scale=1):
            gr.Markdown("### &nbsp;")
            save_btn = gr.Button("💾 Datei anzeigen (Download)")
            file_out = gr.File(label="Letzte generierte Datei")


    gr.Markdown(
        """
---
<div class="footer-note">
<strong>Tipps:</strong> Für bestes Zero-Shot-Cloning: 10–30s saubere Sprachprobe, wenig Hall, möglichst gleichmäßige Lautstärke.  
XTTS v2 unterstützt viele Sprachen; die Aussprache passt du mit der Sprachwahl an.
</div>
"""
    )

    # Events
    set_ref_btn.click(remember_reference_voice, inputs=ref_audio, outputs=ref_status)
    clear_ref_btn.click(clear_ref, outputs=ref_status)
    gen_btn.click(
        generate_tts,
        inputs=[text, lang],
        outputs=[audio_out, status],
        api_name="tts",
    )
    save_btn.click(get_download_path, outputs=file_out, api_name="get_file")

    # Lade das Modell, wenn die UI bereit ist und zeige den Fortschritt an
    demo.load(load_model, outputs=status)


# PyTorch 2.6+ fix for TTS model loading
try:
    import torch
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import XttsAudioConfig, XttsArgs
    from TTS.tts.configs.shared_configs import BaseTTSConfig
    from TTS.config.shared_configs import BaseDatasetConfig
    from coqpit import Coqpit
    # Add all the classes that are in the checkpoint to the safe globals
    torch.serialization.add_safe_globals([XttsConfig, XttsAudioConfig, XttsArgs, BaseTTSConfig, BaseDatasetConfig, Coqpit])
    print("INFO: PyTorch >2.6 patch applied for model loading.")
except (ImportError, AttributeError) as e:
    print(f"INFO: PyTorch >2.6 patch not applied. Error: {e}")
    pass

# Starte die Gradio UI. Das Modell wird jetzt durch demo.load() geladen.
print("Starte Gradio UI...")
demo.launch()
