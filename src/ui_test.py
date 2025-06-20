from PyQt6.QtWidgets import QApplication
from UI.home.page import MainAppWindow

# Run the app
if __name__ == "__main__":
    app = QApplication([])
    with open('history/curr_database.txt', 'r') as f:
        db_path = f.read()
    window = MainAppWindow(db_path)
    window.setMinimumSize(800, 600)
    window.showMaximized()
    app.exec()
    