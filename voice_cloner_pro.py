# voice_cloner_pro.py
import sys
import os
import threading
import sounddevice as sd
import soundfile as sf
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QTextEdit, QLabel, QProgressBar,
                               QTabWidget, QFileDialog, QListWidget, QComboBox)
from PySide6.QtCore import Qt, Signal, QObject

# Coqui TTS importieren
try:
    from TTS.api import TTS
except ImportError:
    print("Bitte installiere TTS: pip install TTS")

# --- Helper Klasse für Threading Updates ---
class WorkerSignals(QObject):
    progress = Signal(int)
    status = Signal(str)

# --- Main GUI Class ---
class VoiceClonerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Cloner Pro")
        self.setGeometry(100, 100, 1000, 600)
        self.signals = WorkerSignals()
        self.signals.progress.connect(self.update_progress)
        self.signals.status.connect(self.update_status)
        self.tts_model = None
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        sidebar = QVBoxLayout()
        sidebar.setAlignment(Qt.AlignTop)
        
        self.tabs = QListWidget()
        self.tabs.addItems(["Aufnahme", "Dataset/Training", "TTS", "Einstellungen"])
        self.tabs.currentRowChanged.connect(self.switch_tab)
        sidebar.addWidget(self.tabs)
        
        self.stack = QTabWidget()
        self.stack.setTabPosition(QTabWidget.North)
        self.stack.addTab(self.record_tab_ui(), "Aufnahme")
        self.stack.addTab(self.training_tab_ui(), "Training")
        self.stack.addTab(self.tts_tab_ui(), "TTS")
        self.stack.addTab(self.settings_tab_ui(), "Einstellungen")
        
        main_layout.addLayout(sidebar, 1)
        main_layout.addWidget(self.stack, 4)
    
    # --- Aufnahme ---
    def record_tab_ui(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        self.record_btn = QPushButton("Aufnahme starten")
        self.record_btn.clicked.connect(self.record_audio)
        layout.addWidget(self.record_btn)
        
        self.play_btn = QPushButton("Abspielen")
        self.play_btn.clicked.connect(self.play_audio)
        layout.addWidget(self.play_btn)
        
        self.record_status = QLabel("Keine Aufnahme")
        layout.addWidget(self.record_status)
        
        tab.setLayout(layout)
        return tab
    
    def record_audio(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Speichern unter", "", "WAV Dateien (*.wav)")
        if not filename:
            return
        
        self.record_status.setText("Aufnahme läuft...")
        duration = 5
        samplerate = 44100
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1)
        sd.wait()
        sf.write(filename, recording, samplerate)
        self.record_status.setText(f"Aufnahme gespeichert: {filename}")
        self.last_recording = filename
    
    def play_audio(self):
        if hasattr(self, "last_recording"):
            data, samplerate = sf.read(self.last_recording, dtype='float32')
            sd.play(data, samplerate)
        else:
            self.record_status.setText("Keine Aufnahme zum Abspielen vorhanden")
    
    # --- Training ---
    def training_tab_ui(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        self.dataset_btn = QPushButton("Dataset auswählen")
        self.dataset_btn.clicked.connect(self.select_dataset)
        layout.addWidget(self.dataset_btn)
        
        self.start_train_btn = QPushButton("Training starten")
        self.start_train_btn.clicked.connect(self.start_training)
        layout.addWidget(self.start_train_btn)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.train_status = QLabel("Nicht gestartet")
        layout.addWidget(self.train_status)
        
        tab.setLayout(layout)
        return tab
    
    def select_dataset(self):
        folder = QFileDialog.getExistingDirectory(self, "Dataset-Ordner auswählen")
        if folder:
            self.dataset_path = folder
            self.train_status.setText(f"Dataset ausgewählt: {folder}")
    
    def start_training(self):
        if not hasattr(self, "dataset_path"):
            self.train_status.setText("Kein Dataset ausgewählt")
            return
        
        self.train_thread = threading.Thread(target=self.train_model)
        self.train_thread.start()
    
    def train_model(self):
        self.signals.status.emit("Training läuft...")
        # Beispiel: Coqui TTS Training (einfacher Dummy, echtes Training kann sehr lange dauern)
        for i in range(101):
            self.signals.progress.emit(i)
            sd.sleep(50)
        self.signals.status.emit("Training abgeschlossen")
    
    # --- TTS ---
    def tts_tab_ui(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        self.tts_text = QTextEdit()
        self.tts_text.setPlaceholderText("Text hier eingeben...")
        layout.addWidget(self.tts_text)
        
        self.voices_combo = QComboBox()
        self.voices_combo.addItems(["deutsch"])  # Platzhalter
        layout.addWidget(self.voices_combo)
        
        self.generate_btn = QPushButton("TTS generieren")
        self.generate_btn.clicked.connect(self.generate_tts)
        layout.addWidget(self.generate_btn)
        
        self.tts_status = QLabel("Bereit")
        layout.addWidget(self.tts_status)
        
        tab.setLayout(layout)
        return tab
    
    def generate_tts(self):
        text = self.tts_text.toPlainText()
        if not text.strip():
            self.tts_status.setText("Bitte Text eingeben")
            return
        
        if self.tts_model is None:
            self.tts_status.setText("Lade TTS Modell...")
            # Deutschsprachiges Modell
            self.tts_model = TTS(model_name="tts_models/de/thorsten/tacotron2-DDC")
            self.tts_status.setText("Modell geladen")
        
        output_file = "tts_output.wav"
        self.tts_model.tts_to_file(text=text, speaker=self.voices_combo.currentText(), file_path=output_file)
        self.tts_status.setText(f"TTS abgeschlossen: {output_file}")
        # Automatisch abspielen
        data, samplerate = sf.read(output_file, dtype='float32')
        sd.play(data, samplerate)
    
    # --- Einstellungen ---
    def settings_tab_ui(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Einstellungen werden hier angezeigt"))
        tab.setLayout(layout)
        return tab
    
    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)
    
    # --- Signals Updates ---
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def update_status(self, text):
        self.train_status.setText(text)

# --- App starten ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VoiceClonerApp()
    window.show()
    sys.exit(app.exec())
