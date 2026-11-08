"""First milestone: floating window and background capture diagnostic."""
import sys
from threading import Event
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from .capture import record
from .live import listen


class CaptureWorker(QThread):
    result = Signal(str)

    def run(self):
        try:
            path = record()
            self.result.emit(f'Saved {path.resolve()} — replay it to verify Chrome audio.')
        except Exception as exc:
            self.result.emit(f'Capture failed: {exc}')


class LiveWorker(QThread):
    reply = Signal(str)
    status = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.stop = Event()

    def run(self):
        try:
            listen(self.stop, self.reply.emit, self.status.emit)
        except Exception as exc:
            self.status.emit(f"Live mode stopped: {exc}")


class Companion(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.live_worker = None
        self.setWindowTitle('Arabic Companion — audio diagnostic')
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.resize(520, 280)
        layout = QVBoxLayout(self)
        title = QLabel('Arabic Companion')
        title.setStyleSheet('font-size: 26px; font-weight: bold')
        layout.addWidget(title)
        self.status = QLabel('Play Arabic in Chrome, then capture 10 seconds.\nThis records all audio on your default playback device.\nUse Start live practice for automatic replies.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.capture = QPushButton('Capture 10 seconds')
        self.capture.clicked.connect(self.start_capture)
        layout.addWidget(self.capture)
        self.reply = QLabel()
        self.reply.setWordWrap(True)
        self.reply.setStyleSheet("font-size: 18px")
        self.reply.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.reply)
        self.live = QPushButton("Start live practice")
        self.live.clicked.connect(self.toggle_live)
        layout.addWidget(self.live)

    def toggle_live(self):
        if self.live_worker is not None:
            self.live_worker.stop.set()
            self.live.setEnabled(False)
            self.status.setText("Stopping…")
            return
        self.capture.setEnabled(False)
        self.reply.clear()
        self.live.setText("Stop listening")
        self.live_worker = LiveWorker(self)
        self.live_worker.status.connect(self.status.setText)
        self.live_worker.reply.connect(self.show_reply)
        self.live_worker.finished.connect(self.live_finished)
        self.live_worker.finished.connect(self.live_worker.deleteLater)
        self.live_worker.start()

    def show_reply(self, text):
        if self.live_worker is not None and not self.live_worker.stop.is_set():
            self.reply.setText(text)
            self.status.setText("Listening for the next question")

    def live_finished(self):
        self.live_worker = None
        self.live.setEnabled(True)
        self.capture.setEnabled(True)
        self.live.setText("Start live practice")
        if self.status.text() == "Stopping…":
            self.status.setText("Stopped")

    def start_capture(self):
        self.live.setEnabled(False)
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
        self.live.setEnabled(True)

    def closeEvent(self, event):
        if self.live_worker is not None:
            self.live_worker.stop.set()
            self.live.setEnabled(False)
            self.status.setText('Stopping… close again when stopped.')
            event.ignore()
        elif self.worker is not None:
            self.status.setText('Please wait for the bounded capture to finish before closing.')
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    window = Companion()
    window.show()
    sys.exit(app.exec())
