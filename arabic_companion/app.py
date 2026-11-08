"""First milestone: floating window and background capture diagnostic."""
import sys
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from .capture import record


class CaptureWorker(QThread):
    result = Signal(str)

    def run(self):
        try:
            path = record()
            self.result.emit(f'Saved {path.resolve()} — replay it to verify Chrome audio.')
        except Exception as exc:
            self.result.emit(f'Capture failed: {exc}')


class Companion(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.setWindowTitle('Arabic Companion — audio diagnostic')
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.resize(520, 280)
        layout = QVBoxLayout(self)
        title = QLabel('Arabic Companion')
        title.setStyleSheet('font-size: 26px; font-weight: bold')
        layout.addWidget(title)
        self.status = QLabel('Play Arabic in Chrome, then capture 10 seconds.\nThis records all audio on your default playback device.\nTranscription and reply generation are not connected yet.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.capture = QPushButton('Capture 10 seconds')
        self.capture.clicked.connect(self.start_capture)
        layout.addWidget(self.capture)

    def start_capture(self):
        self.capture.setEnabled(False)
        self.status.setText('Recording for 10 seconds…')
        self.worker = CaptureWorker(self)
        self.worker.result.connect(self.status.setText)
        self.worker.finished.connect(lambda: self.capture.setEnabled(True))
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.finished.connect(self.finished)
        self.worker.start()

    def finished(self):
        self.worker = None

    def closeEvent(self, event):
        if self.worker is not None:
            self.status.setText('Please wait for the bounded capture to finish before closing.')
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    window = Companion()
    window.show()
    sys.exit(app.exec())
