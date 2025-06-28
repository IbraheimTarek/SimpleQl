from UI.home.widgets.main_content import MainContent
from UI.home.widgets.sidebar import Sidebar
from database_manager import DBManager

from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout                

class MainAppWindow(QMainWindow):
    """Main application window with sidebar and content area"""
    
    def __init__(self, db_path):
        super().__init__()
        self.db_manager = DBManager(db_path)
        self.initial = True
        self.init_ui()
 
    def init_ui(self):
        """Initialize the main window UI"""
        self.setWindowTitle("SimpleQL")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8FAFC;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main content area
        self.main_content = MainContent(self.db_manager, self.initial)
        
        # Sidebar
        self.sidebar = Sidebar(self.db_manager)

        # Connect signals
        self.main_content.text_input.query_executed.connect(self.sidebar.add_query_result)
        self.sidebar.result_clicked.connect(self.main_content.load_result_from_file)
        self.main_content.new_question.connect(self.sidebar.clear_checked)

        # Add widgets to layout
        main_layout.addWidget(self.main_content, 1)  # Takes remaining space
        main_layout.addWidget(self.sidebar)  # Fixed width
        
        central_widget.setLayout(main_layout)

    def resizeEvent(self, event):
        """
        Override for `resizeEvent` event for QMainWindow.
        Triggers when the window is resized.
        """
        super().resizeEvent(event)
        self.main_content.text_input.on_text_changed()
        
