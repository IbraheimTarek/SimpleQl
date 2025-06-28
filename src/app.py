import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from UI.home.page import MainAppWindow
from UI.initial_page.page import InitialPage

class App(QApplication):
    """
    Class for running the application.

    Args:
        argv (Union[Optional, list]): 
    """
    
    def __init__(self, argv=[]):
        super().__init__(argv)
        self.init_ui()
        
    def init_ui(self):
        if os.path.exists('history/curr_database.txt'):
            # There is an already connected database, Load it and show home page
            with open('history/curr_database.txt', 'r') as f:
                db_path = f.read()
            self.window = MainAppWindow(db_path)
            self.window.setWindowIcon(QIcon("src/UI/assets/gp_logo_small.png"))
            self.window.sidebar.db_changed.connect(self.changeDatabase)
            self.window.showMaximized()
        else: 
            # Show setup page
            self.window = InitialPage()
            self.window.show()
            self.window.connected.connect(self.changeDatabase)
        
    def changeDatabase(self, db_path):
        """
        Changes the database connected and initialized a new home page.

        Args:
            db_path (str): path to database file
        """
        if db_path:
            with open('history/curr_database.txt', 'w') as f:
                f.write(db_path)
            self.window.close()
            if hasattr(self.window, 'sidebar'):
                self.window.sidebar.db_changed.disconnect(self.changeDatabase)
            self.window = MainAppWindow(db_path)
            self.window.setWindowIcon(QIcon("src/UI/assets/gp_logo_small.png"))
            self.window.sidebar.db_changed.connect(self.changeDatabase)
            self.window.showMaximized()

# Run the app
if __name__ == "__main__":
    app = App()
    app.exec()
    