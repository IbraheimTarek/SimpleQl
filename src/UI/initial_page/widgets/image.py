from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QSize
import os

class ImageWidget(QLabel):
    """
    widget to display an image scaled to a maximum size

    Args:
        image_path (str): path to image
        max_size (QSize): Maximum size of image
    """
    def __init__(self, image_path: str, max_size: QSize = QSize(800, 600), parent=None):
        super().__init__(parent)

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        abs_path = os.path.abspath(image_path)
        if not os.path.exists(abs_path):
            self.setText("Couldn't load image")
            return

        pixmap = QPixmap(abs_path)

        # Scale the image to fit max_size while keeping aspect ratio
        scaled = pixmap.scaled(
            max_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)
