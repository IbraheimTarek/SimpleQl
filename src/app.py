import os

from PyQt6.QtWidgets import QApplication
from UI.home.page import MainAppWindow
from UI.initial_page.page import InitialPage

class App(QApplication):
    
    def __init__(self, argv=[]):
        super().__init__(argv)
        self.init_ui()
        
    def init_ui(self):
        if os.path.exists('history/curr_database.txt'):
            with open('history/curr_database.txt', 'r') as f:
                db_path = f.read()
            self.window = MainAppWindow(db_path)
            self.window.showMaximized()
        else:
            window = InitialPage()
            window.show()
        
        self.window.sidebar.db_changed.connect(self.changeDatabase)

    def changeDatabase(self, db_path):
        if db_path:
            print("Selected file:", db_path)
            with open('history/curr_database.txt', 'w') as f:
                f.write(db_path)
            self.window.close()
            self.window.sidebar.db_changed.disconnect(self.changeDatabase)
            self.window = MainAppWindow(db_path)
            self.window.sidebar.db_changed.connect(self.changeDatabase)
            self.window.showMaximized()

# Run the app
if __name__ == "__main__":
    app = App([])
    app.exec()
    