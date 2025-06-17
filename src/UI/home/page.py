import os
from datetime import datetime
import json

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QFrame, QTextEdit,
                            QScrollArea, QSpacerItem, QSizePolicy, QSplitter, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor, QFontMetrics


class IntegratedTextEdit(QFrame):
    """Custom text edit with integrated execute button"""
    
    query_executed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_lines = 3
        self.min_lines = 1
        self.line_height = 17
        self.base_height = 36
        self.init_ui()
        
    def init_ui(self):
        """Initialize the integrated text edit UI"""
        # Main container styling
        self.setStyleSheet("""
            QFrame {
                border: 2px solid #E5E7EB;
                border-radius: 8px;
                background-color: #FAFAFA;
            }
            QFrame:focus-within {
                border-color: #14B8A6;
                background-color: white;
            }
        """)
        
        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(8)
        
        # Text edit
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("SELECT * FROM your_table_name;")
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: none;
                background-color: transparent;
                padding: 8px 12px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 14px;
                color: #1F2937;
                selection-background-color: #14B8A6;
                selection-color: white;
            }
            QTextEdit:focus {
                outline: none;
            }
        """)
        
        # Set up text edit properties
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        
        # Calculate line height and set initial height
        self.set_height_for_lines(self.min_lines)
        
        # Connect text change signal
        self.text_edit.textChanged.connect(self.on_text_changed)
        
        # Execute button
        self.execute_button = QPushButton("▶")
        self.execute_button.setFixedSize(36, 36)
        self.execute_button.setToolTip("Execute Query (Ctrl+Enter)")
        self.execute_button.setStyleSheet("""
            QPushButton {
                background-color: #14B8A6;
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background-color: #0F766E;
            }
            QPushButton:pressed:enabled {
                background-color: #0D5B56;
            }
            QPushButton:disabled {
                background-color: #CBD5E1;
                color: #9CA3AF;
            }
        """)
        self.execute_button.clicked.connect(self.execute_query)
        self.execute_button.setEnabled(False)  # Initially disabled
        
        # Add widgets to layout
        main_layout.addWidget(self.text_edit, 1)
        
        # Button container to center the button vertically
        button_container = QFrame()
        button_layout = QVBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addStretch()
        button_layout.addWidget(self.execute_button)
        button_layout.addStretch()
        button_container.setLayout(button_layout)
        
        main_layout.addWidget(button_container)
        
        self.setLayout(main_layout)
        
        # Set initial focus to text edit
        self.text_edit.setFocus()
        
    def set_height_for_lines(self, lines):
        """Set the height of the text edit for a specific number of lines"""
            
        height = self.base_height + (self.line_height * lines)
        self.setFixedHeight(int(height))
        
    def on_text_changed(self):
        """Handle text changes - adjust height and button state"""
        # Update button state
        text = self.text_edit.toPlainText().strip()
        self.execute_button.setEnabled(bool(text))
        
        # Adjust height
        doc = self.text_edit.document()
        doc_height = doc.size().height()
        
        if self.line_height > 0:
            lines_needed = max(1, int(doc_height / self.line_height))
            
        display_lines = min(lines_needed, self.max_lines)
        self.set_height_for_lines(display_lines)
        
        # Handle scrolling
        if lines_needed > self.max_lines:
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    
    def execute_query(self):
        """Execute the query"""
        query = self.text_edit.toPlainText().strip()
        if query:
            self.query_executed.emit(query)
    
    def get_text(self):
        """Get the current text"""
        return self.text_edit.toPlainText()
    
    def set_text(self, text):
        """Set the text"""
        self.text_edit.setText(text)
    
    def clear(self):
        """Clear the text"""
        self.text_edit.clear()
    
    def set_placeholder_text(self, text):
        """Set placeholder text"""
        self.text_edit.setPlaceholderText(text)

class QueryResultButton(QPushButton):
    """Custom button for query results in sidebar"""
    
    def __init__(self, query_id, query_text, timestamp, file_path, parent=None):
        super().__init__(parent)
        self.query_id = query_id
        self.query_text = query_text
        self.timestamp = timestamp
        
        # Create display text
        short_query = query_text[:30] + "..." if len(query_text) > 30 else query_text
        display_text = f"Query #{query_id}\n{short_query}\n{timestamp}"
        
        self.setText(display_text)
        self.setFixedHeight(80)
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

class DynamicSidebar(QFrame):
    """Dynamic sidebar that starts empty and adds query results"""
    
    result_clicked = pyqtSignal(str, str)  # file_path, query_text
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.query_buttons = []
        self.query_counter = 0
        self.results_directory = "query_results"  # Directory to store results
        self.init_ui()
        self.create_results_directory()
        
    def create_results_directory(self):
        """Create directory for storing query results"""
        if not os.path.exists(self.results_directory):
            os.makedirs(self.results_directory)
            
    def init_ui(self):
        """Initialize sidebar UI"""
        self.setFixedWidth(280)
        self.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border-left: 1px solid #E2E8F0;
                padding: 0px;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 20, 16, 20)
        main_layout.setSpacing(12)
        
        # Sidebar title
        self.title_label = QLabel("Query Results")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #1E293B;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 0px;
                border-bottom: 2px solid #14B8A6;
                margin-bottom: 16px;
            }
        """)
        main_layout.addWidget(self.title_label)
        
        # Scrollable area for query buttons
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #F1F5F9;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #CBD5E1;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #94A3B8;
            }
        """)
        
        # Container widget for buttons
        self.buttons_container = QWidget()
        self.buttons_layout = QVBoxLayout()
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(4)
        
        # Empty state label
        self.empty_label = QLabel("No queries executed yet.\nExecute a query to see results here.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #64748B;
                font-size: 14px;
                padding: 40px 20px;
                background-color: rgba(241, 245, 249, 0.5);
                border: 2px dashed #CBD5E1;
                border-radius: 8px;
                margin: 20px 0px;
            }
        """)
        self.buttons_layout.addWidget(self.empty_label)
        
        # Add stretch to push buttons to top
        self.buttons_layout.addStretch()
        
        self.buttons_container.setLayout(self.buttons_layout)
        scroll_area.setWidget(self.buttons_container)
        
        main_layout.addWidget(scroll_area)
        
        # Clear all button
        self.clear_button = QPushButton("Clear All Results")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
            QPushButton:pressed {
                background-color: #B91C1C;
            }
            QPushButton:disabled {
                background-color: #9CA3AF;
                color: #D1D5DB;
            }
        """)
        self.clear_button.clicked.connect(self.clear_all_results)
        self.clear_button.setEnabled(False)  # Disabled initially
        main_layout.addWidget(self.clear_button)
        
        # Footer info
        footer_label = QLabel("SimpleQL v1.0\nQuery History")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setStyleSheet("""
            QLabel {
                color: #64748B;
                font-size: 11px;
                padding: 16px 8px;
                border-top: 1px solid #E2E8F0;
                background-color: rgba(226, 232, 240, 0.3);
                border-radius: 4px;
                margin-top: 10px;
            }
        """)
        main_layout.addWidget(footer_label)
        
        self.setLayout(main_layout)
    
    def add_query_result(self, query_text, result_data):
        """Add a new query result to the sidebar"""
        self.query_counter += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Create file path for storing result
        filename = f"query_{self.query_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = os.path.join(self.results_directory, filename)
        
        # Save result data to file
        result_info = {
            "query_id": filename,
            "query_text": query_text,
            "timestamp": timestamp,
            "execution_time": datetime.now().isoformat(),
            "result_data": result_data
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result_info, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving result: {e}")
            return
        
        # Remove empty label if this is the first query
        if len(self.query_buttons) == 0:
            self.empty_label.hide()
            self.clear_button.setEnabled(True)
        
        # Create new button
        button = QueryResultButton(
            filename, 
            query_text, 
            timestamp, 
        )
        button.clicked.connect(lambda: self.on_result_clicked(button))
        
        # Add button to layout (insert at top, after removing stretch)
        self.buttons_layout.removeItem(self.buttons_layout.itemAt(self.buttons_layout.count() - 1))  # Remove stretch
        self.buttons_layout.insertWidget(1, button)  # Insert after empty label (which is hidden)
        self.buttons_layout.addStretch()  # Add stretch back
        
        # Add to tracking list
        self.query_buttons.append(button)
        
        # Auto-select the new button
        self.select_button(button)
        
        # Update title to show count
        self.title_label.setText(f"Query Results ({len(self.query_buttons)})")
    
    def on_result_clicked(self, clicked_button):
        """Handle result button click"""
        self.select_button(clicked_button)
        self.result_clicked.emit(clicked_button.file_path, clicked_button.query_text)
    
    def select_button(self, selected_button):
        """Select a button and deselect others"""
        for button in self.query_buttons:
            button.setChecked(button == selected_button)
    
    def clear_all_results(self):
        """Clear all query results"""
        reply = QMessageBox.question(
            self, 
            'Clear All Results', 
            'Are you sure you want to clear all query results?\nThis will delete all saved result files.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove all buttons
            for button in self.query_buttons:
                button.deleteLater()
                # Try to delete the associated file
                try:
                    if os.path.exists(button.file_path):
                        os.remove(button.file_path)
                except Exception as e:
                    print(f"Error deleting file {button.file_path}: {e}")
            
            self.query_buttons.clear()
            self.query_counter = 0
            
            # Show empty label again
            self.empty_label.show()
            self.clear_button.setEnabled(False)
            
            # Reset title
            self.title_label.setText("Query Results")
            
            # Clear main content
            self.result_clicked.emit("", "")

class MainContent(QFrame):
    """Main content area with textbox and label"""
    
    query_executed = pyqtSignal(str, str)  # query_text, result_data

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize main content UI"""
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: none;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Title area
        self.title_label = QLabel("SQL Query Editor")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #1E293B;
                font-size: 24px;
                font-weight: bold;
                padding-bottom: 8px;
            }
        """)
        layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Description
        self.description_label = QLabel("Enter your SQL queries below and execute them against the connected database.")
        self.description_label.setStyleSheet("""
            QLabel {
                color: #64748B;
                font-size: 14px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(self.description_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Text input area
        # Integrated text input with execute button
        self.text_input = IntegratedTextEdit()
        self.text_input.query_executed.connect(self.execute_query)
        layout.addWidget(self.text_input)
        
        # Additional action buttons
        button_layout = QHBoxLayout()
        
        clear_button = QPushButton("Clear")
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #6B7280;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
            QPushButton:pressed {
                background-color: #374151;
            }
        """)
        clear_button.clicked.connect(self.clear_input)
        
        button_layout.addWidget(clear_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Results area placeholder
        results_label = QLabel("Query Results:")
        results_label.setStyleSheet("""
            QLabel {
                color: #374151;
                font-size: 16px;
                font-weight: bold;
                margin-top: 20px;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(results_label)
        
        self.results_area = QTextEdit()
        self.results_area.setReadOnly(True)
        self.results_area.setPlaceholderText("Query results will appear here...")
        self.results_area.setStyleSheet("""
            QTextEdit {
                border: 2px solid #E5E7EB;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                background-color: #F9FAFB;
                color: #1F2937;
            }
        """)
        self.results_area.setMinimumHeight(150)
        layout.addWidget(self.results_area)

        # Results area placeholder
        results_label = QLabel("Query Results:")
        results_label.setStyleSheet("""
            QLabel {
                color: #374151;
                font-size: 16px;
                font-weight: bold;
                margin-top: 20px;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(results_label)
        
        self.results_area = QTextEdit()
        self.results_area.setReadOnly(True)
        self.results_area.setPlaceholderText("Query results will appear here...")
        self.results_area.setStyleSheet("""
            QTextEdit {
                border: 2px solid #E5E7EB;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                background-color: #F9FAFB;
                color: #1F2937;
            }
        """)
        self.results_area.setMinimumHeight(150)
        layout.addWidget(self.results_area)
        
        self.setLayout(layout)
    
    def execute_query(self, query):
        """Handle query execution and create sidebar entry"""
        # Simulate query execution and generate result data
        result_data = f"""Query executed successfully!
Query: {query}
Execution time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Sample Results:
+----+----------+-------+
| ID | Name     | Value |
+----+----------+-------+
| 1  | Sample   | 100   |
| 2  | Data     | 200   |
| 3  | Result   | 300   |
+----+----------+-------+

Rows affected: 3
Execution time: 0.045 seconds"""
        
        # Show results in main area
        self.results_area.setText(result_data)
        
        # Emit signal to parent to add to sidebar
        self.query_executed.emit(query, result_data)
    
    def clear_input(self):
        """Clear the input text"""
        self.text_input.clear()
    
    def load_result_from_file(self, file_path, query_text):
        """Load and display result from file"""
        if not file_path:  # Empty path means clear results
            self.results_area.clear()
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                result_info = json.load(f)
            
            # Display the loaded result
            self.results_area.setText(result_info.get('result_data', 'No result data found'))
            
            # Optionally load the query back into the editor
            # self.text_input.setText(result_info.get('query_text', ''))
            
        except Exception as e:
            self.results_area.setText(f"Error loading result from {file_path}:\n{str(e)}")

class MainAppWindow(QMainWindow):
    """Main application window with sidebar and content area"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the main window UI"""
        self.setWindowTitle("SimpleQL - Database Management Tool")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set window background
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8FAFC;
            }
        """)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create main content area
        self.main_content = MainContent()
        
        # Create sidebar
        self.sidebar = DynamicSidebar()

        # Connect signals
        self.main_content.query_executed.connect(self.sidebar.add_query_result)
        self.sidebar.result_clicked.connect(self.main_content.load_result_from_file)
        
        # Add widgets to layout
        main_layout.addWidget(self.main_content, 1)  # Takes remaining space
        main_layout.addWidget(self.sidebar)  # Fixed width
        
        central_widget.setLayout(main_layout)
        
        # Center window on screen
        self.center_window()
        
    def center_window(self):
        """Center the window on the screen"""
        screen = QApplication.primaryScreen().geometry()
        window = self.geometry()
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        self.move(x, y)

    def resizeEvent(self, event):
        """Trigger when the window is resized"""
        super().resizeEvent(event)
        self.main_content.text_input.on_text_changed()
