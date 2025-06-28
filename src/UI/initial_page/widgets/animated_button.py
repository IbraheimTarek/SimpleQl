from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QPropertyAnimation, QSize, QEasingCurve, Qt
from PyQt6.QtGui import QFont, QIcon

class AnimatedButton(QPushButton):
    """
    An animated button for the setup screen

    Args:
        text (str): the text to be displayed in the button
        icon (Union[None|QIcon]): the icon to be displayed in the button
    """
    def __init__(self, text, icon: QIcon = None):
        super().__init__(text)
        self.anim_enabled = True
        self.setStyleSheet("""
            QPushButton {
                background-color: #94E8F0;
                color: #323253;
                padding: 10px 20px;
                border-radius: 10px;
                font-size: 16px;
            }
        """)
        font = QFont()
        font.setBold(True)
        self.setFont(font)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)

        self.default_size = QSize(300, 40)
        self.hover_size = QSize(320, 45)
        self.setMinimumSize(self.default_size)

        # Apply icon if provided
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(20, 20)) 

        # Setup animation
        self.anim = QPropertyAnimation(self, b"minimumSize")
        self.anim.setDuration(80)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def enterEvent(self, event):
        """
        Override for the `enterEvent` event for QPushButton
        """
        if not self.anim_enabled:
            return
        self.anim.stop()
        self.anim.setStartValue(self.minimumSize())
        self.anim.setEndValue(self.hover_size)
        self.anim.start()

        self.setStyleSheet("""
            QPushButton {
                background-color: #89CFD7;
                color: #323253;
                padding: 10px 20px;
                border-radius: 10px;
                font-size: 16px;
            }
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """
        Override for the `leaveEvent` event for QPushButton
        """
        if not self.anim_enabled:
            return
        self.anim.stop()
        self.anim.setStartValue(self.minimumSize())
        self.anim.setEndValue(self.default_size)
        self.anim.start()

        self.setStyleSheet("""
            QPushButton {
                background-color: #94E8F0;
                color: #323253;
                padding: 10px 20px;
                border-radius: 10px;
                font-size: 16px;
            }
        """)
        super().leaveEvent(event)
