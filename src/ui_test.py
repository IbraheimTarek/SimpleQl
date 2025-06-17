from PyQt6.QtWidgets import QApplication
from UI.home.page import MainAppWindow

# Run the app
if __name__ == "__main__":
    app = QApplication([])
    window = MainAppWindow()
    window.show()
    app.exec()