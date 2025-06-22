import os

from PyQt6.QtWidgets import QApplication
from UI.home.page import MainAppWindow
from UI.initial_page.page import InitialPage

# Run the app
if __name__ == "__main__":
    app = QApplication([])
    if os.path.exists('history/curr_database.txt'):
        with open('history/curr_database.txt', 'r') as f:
            db_path = f.read()
        window = MainAppWindow(db_path)
        window.showMaximized()
    else:
        window = InitialPage()
        window.show()
    app.exec()
    