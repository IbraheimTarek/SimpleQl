from PyQt6.QtWidgets import QLabel, QDialog, QVBoxLayout
from PyQt6.QtGui import QPixmap, QMouseEvent
from PyQt6.QtCore import Qt, QSize
import os

class PlotWidget(QLabel):
    def __init__(self, image_path: str, max_size: QSize = QSize(200, 150), parent=None):
        super().__init__(parent)
        self.image_path = os.path.abspath(image_path)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if not os.path.exists(self.image_path):
            self.setText("Couldn't load image")
            return

        pixmap = QPixmap(self.image_path)
        scaled = pixmap.scaled(
            max_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse click event"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_image_dialog()

    def open_image_dialog(self):
        """Open full-size image in a popup window"""
        dialog = QDialog()
        dialog.setWindowTitle("Image Viewer")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)

        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(self.image_path)

        # Scale to fit but allow larger window resizing
        label.setPixmap(pixmap.scaled(dialog.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(label)

        # Ensure image resizes with window
        def resizeEvent(event):
            label.setPixmap(pixmap.scaled(dialog.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            QDialog.resizeEvent(dialog, event)

        dialog.resizeEvent = resizeEvent
        dialog.exec()
