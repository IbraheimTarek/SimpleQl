from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt


class ResultButton(QWidget):
    def __init__(self, query_text, query_id, parent=None):
        super().__init__(parent)
        self.query_id = query_id
        self.query_text = query_text

        self.setFixedHeight(40)
        self.setStyleSheet("""
            QWidget {
                border-radius: 8px;
            }
            QWidget:hover {
                background-color: #CBD1CC;
                border-color: #14B8A6;
            }
        """)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Text Button
        self.button = QPushButton()
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.setCheckable(True)
        self.button.setFixedHeight(40)
        self.button.setStyleSheet("""
            QPushButton {
                color: #475569;
                border: none;
                text-align: left;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                color: #1E293B;
            }
            QPushButton:checked {
                background-color: #14B8A6;
                color: white;
                font-weight: 600;
            }
        """)

        short_query = self.query_text[:35] + "..." if len(self.query_text) > 35 else self.query_text
        self.button.setText(short_query)
        self.layout.addWidget(self.button)

        # Icon Button
        self.icon_button = QPushButton(self)
        self.icon_button.setIcon(QIcon("src/UI/assets/delete.png"))
        self.icon_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_button.setFixedSize(20, 20)
        self.icon_button.move(self.width() - 26, 10)
        self.icon_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
        """)
        self.icon_button.hide()  # Initially hidden

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.icon_button.move(self.width() - 26, 10)

    def enterEvent(self, event):
        """Show icon button on hover"""
        self.icon_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide icon button when not hovering"""
        self.icon_button.hide()
        super().leaveEvent(event)

    def setChecked(self, checked: bool):
        self.button.setChecked(checked)

    def isChecked(self):
        return self.button.isChecked()

    def clicked(self, callback):
        self.button.clicked.connect(callback)

    def on_icon_clicked(self, callback):
        self.icon_button.clicked.connect(callback)
