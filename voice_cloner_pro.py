import os
import sys
import torch
from TTS.api import TTS
from PyQt5 import QtWidgets, QtGui, QtCore

# HACK: Add XttsConfig to torch safe globals
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import XttsAudioConfig
from TTS.config import Coqpit
import torch.serialization
torch.serialization.add_safe_globals([Coqpit, XttsConfig, XttsAudioConfig])

# -----------------------------
# Einstellungen für Coqui Cache
# -----------------------------
os.environ["COQUI_TTS_CACHE"] = "/workspace/xtts-gitpod/model_cache"
os.makedirs(os.environ["COQUI_TTS_CACHE"], exist_ok=True)

MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
tts_model = None

# -----------------------------
# Modell laden
# -----------------------------
def load_model():
    global tts_model
    print("📥 Lade Sprachmodell herunter und initialisiere...")
    try:
        tts_model = TTS(MODEL_NAME)
        print("✅ Modell erfolgreich geladen!")
    except Exception as e:
        print(f"❌ Fehler beim Laden des Modells: {e}")
        sys.exit(1)

# -----------------------------
# GUI-Klasse
# -----------------------------
class VoiceClonerApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Cloner Pro")
        self.setGeometry(200, 200, 600, 400)
        self.speaker_wav_path = None

        layout = QtWidgets.QVBoxLayout()

        self.text_input = QtWidgets.QTextEdit()
        self.text_input.setPlaceholderText("Hier den zu klonenden Text eingeben...")

        self.select_speaker_button = QtWidgets.QPushButton("Stimm-Audio auswählen (.wav)")
        self.select_speaker_button.clicked.connect(self.select_speaker_file)

        self.speaker_path_label = QtWidgets.QLabel("Keine Stimm-Audio ausgewählt.")
        self.speaker_path_label.setAlignment(QtCore.Qt.AlignCenter)

        self.speak_button = QtWidgets.QPushButton("🔊 Stimme klonen und Text sprechen")
        self.speak_button.clicked.connect(self.text_to_speech)
        
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.hide()

        layout.addWidget(self.text_input)
        layout.addWidget(self.select_speaker_button)
        layout.addWidget(self.speaker_path_label)
        layout.addWidget(self.speak_button)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def select_speaker_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Wähle eine WAV-Datei als Stimmvorlage", "", "WAV-Dateien (*.wav)")
        if file_path:
            self.speaker_wav_path = file_path
            self.speaker_path_label.setText(f"Vorlage: {os.path.basename(file_path)}")

    def text_to_speech(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte geben Sie einen Text ein.")
            return

        if not self.speaker_wav_path:
            QtWidgets.QMessageBox.warning(self, "Fehler", "Bitte wählen Sie eine Stimm-Audio-Datei aus.")
            return
            
        self.speak_button.setEnabled(False)
        self.progress_bar.show()

        try:
            output_path = "stimme_geklont.wav"
            # Führe die Sprachsynthese in einem separaten Thread aus, um die GUI nicht zu blockieren
            worker = Worker(tts_model.tts_to_file, text=text, speaker_wav=self.speaker_wav_path, language="de", file_path=output_path)
            worker.signals.finished.connect(self.on_synthesis_finished)
            worker.signals.error.connect(self.on_synthesis_error)
            QtCore.QThreadPool.globalInstance().start(worker)

        except Exception as e:
            self.on_synthesis_error(e)

    def on_synthesis_finished(self):
        self.progress_bar.hide()
        self.speak_button.setEnabled(True)
        QtWidgets.QMessageBox.information(self, "Fertig", f"Die geklonte Stimme wurde erfolgreich in 'stimme_geklont.wav' gespeichert.")

    def on_synthesis_error(self, e):
        self.progress_bar.hide()
        self.speak_button.setEnabled(True)
        QtWidgets.QMessageBox.critical(self, "Fehler", f"Die Sprachsynthese ist fehlgeschlagen: {e}")

class WorkerSignals(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(Exception)

class Worker(QtCore.QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @QtCore.pyqtSlot()
    def run(self):
        try:
            self.fn(*self.args, **self.kwargs)
        except Exception as e:
            self.signals.error.emit(e)
        else:
            self.signals.finished.emit()

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    load_model()
    app = QtWidgets.QApplication(sys.argv)
    window = VoiceClonerApp()
    window.show()
    sys.exit(app.exec_())
