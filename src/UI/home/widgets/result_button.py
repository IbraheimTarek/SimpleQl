from PyQt6.QtWidgets import QPushButton

class ResultButton(QPushButton):
    """Custom button for query results in sidebar"""
    
    def __init__(self, query_text, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.query_text = query_text
        # Create display text
        short_query = self.query_text[:35] + "..." if len(self.query_text) > 30 else self.query_text
        
        self.setText(short_query)
        self.setFixedHeight(40)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 8px 12px;
                text-align: left;
                font-size: 12px;
                font-weight: 500;
                margin: 2px 0px;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #1E293B;
                border-color: #14B8A6;
            }
            QPushButton:pressed {
                background-color: #E2E8F0;
            }
            QPushButton:checked {
                background-color: #14B8A6;
                color: white;
                font-weight: 600;
                border-color: #14B8A6;
            }
        """)
        self.setCheckable(True)
