import os
from datetime import datetime
import json
import pandas as pd
import shutil

from plotter.Plotter import DataVizTool
from UI.home.widgets.result_button import ResultButton

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QMessageBox, QFileDialog                          
from PyQt6.QtCore import Qt, pyqtSignal


class Sidebar(QFrame):
    """Dynamic sidebar that starts empty and adds query results"""
    
    result_clicked = pyqtSignal(str)  # file_path
    db_changed = pyqtSignal(str) # file_path
    
    def __init__(self, db_manager, query_counter=0, query_buttons : list = [], parent=None):
        super().__init__(parent)
        self.query_buttons = query_buttons
        self.curr_button = None
        self.query_counter = query_counter
        self.db_manager = db_manager
        self.db_name = db_manager.db_name
        self.results_directory = f"history/databases/{self.db_name}/query_results"  # Directory to store results
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
                padding: 0px;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 20, 16, 20)
        main_layout.setSpacing(12)
        
        # Sidebar title
        self.title_label = QLabel("تاريخ الاسئلة")
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
                background-color: transparent;
                border-radius: 8px;
            }
            QScrollBar:vertical {
                background-color: #F1F5F9;
                width: 8px;
                padding: 0 0 0 4px;
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
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                width: 0px;
                border: none;
                background: none;
            }
        """)
        
        # Container widget for buttons
        self.buttons_container = QWidget()
        self.buttons_container.setStyleSheet("""
            border-radius: 8px;
        """)
        self.buttons_layout = QVBoxLayout()
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(4)
        
        # Empty state label
        self.empty_label = QLabel("لم يتم تنفيذ اي اسئلة بعد \n قم بتنفيذ اي سؤال عن بياناتك ")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("""
            QLabel {
                color: #64748B;
                font-size: 14px;
                padding: 40px 0;
                background-color: rgba(241, 245, 249, 0.5);
                border: 2px dashed #CBD5E1;
                border-radius: 8px;
            }
        """)
        self.buttons_layout.addWidget(self.empty_label)
        # Add stretch to push buttons to top
        self.buttons_layout.addStretch()
        
        self.buttons_container.setLayout(self.buttons_layout)
        scroll_area.setWidget(self.buttons_container)
        
        main_layout.addWidget(scroll_area)

        # Clear all button
        self.clear_button = QPushButton("حذف التاريخ")
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
        self.clear_button.setEnabled(False) 

        main_layout.addWidget(self.clear_button)

        # Change DB button
        self.change_db_button = QPushButton("اختيار بيانات جديدة")
        self.change_db_button.setStyleSheet("""
            QPushButton {
                background-color: #14B8A6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #0F766E;
            }
            QPushButton:pressed {
                background-color: #0D5B56;
            }
            QPushButton:disabled {
                background-color: #CBD5E1;
                color: #D1D5DB;
            }
        """)
        self.change_db_button.clicked.connect(self.changeDatabase)
        main_layout.addWidget(self.change_db_button)

        self.load_query_results()

        if self.query_counter != 0:
            self.empty_label.hide()
        
        self.setLayout(main_layout)
    
    def add_query_result(self, query_text, query_sql, rows, columns):
        """Add a new query result to the sidebar"""
        self.query_counter += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Create file path for storing result
        filename = f"{self.query_counter}.json"
        dir = self.results_directory + f"/{self.query_counter}"
        os.makedirs(dir)
        file_path = os.path.join(dir, filename)
        
        # Save result data to file
        result_info = {
            "query_id": self.query_counter,
            "query_text": query_text,
            "timestamp": timestamp,
            "query_sql": query_sql,
            "rows": rows,
            "columns": columns,
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result_info, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving result: {e}")
            return
        
        # Make plots
        df = pd.DataFrame(rows, columns=columns)
        plotter = DataVizTool(df, f"{self.results_directory}/{self.query_counter}/plots")
        plotter._run("Plot automatically")
        
        # Remove empty label if this is the first query
        if len(self.query_buttons) == 0:
            self.empty_label.hide()
            self.clear_button.setEnabled(True)
        
        # Create new button
        button = ResultButton(
            query_text,
            self.query_counter
        )
        button.clicked(lambda: self.on_result_clicked(button))
        button.on_icon_clicked(lambda: self.clear_result(button.query_id))
        
        # Add button to layout (insert at top, after removing stretch)
        self.buttons_layout.removeItem(self.buttons_layout.itemAt(self.buttons_layout.count() - 1))  # Remove stretch
        self.buttons_layout.insertWidget(1, button)  # Insert after empty label (which is hidden)
        self.buttons_layout.addStretch()  # Add stretch back
        
        # Add to tracking list
        self.query_buttons.append(button)
        
        # Auto-select the new button
        self.on_result_clicked(button)
    
    def load_query_results(self):
        if not os.path.isdir(self.results_directory):
            os.makedirs(self.results_directory)
            self.query_counter = 0

        results = os.listdir(self.results_directory)
        if len(results) == 0:
            self.query_counter = 0
        else:
            dirs = sorted(results, key=lambda x: int(x))
            self.query_counter = int(dirs[len(dirs) - 1])

            for dir in reversed(dirs):
                file_path = os.path.join(self.results_directory, dir + f"/{int(dir)}.json")
                print(file_path)
                with open(file_path, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                button = ResultButton(
                    result['query_text'],
                    int(dir)
                )
                button.clicked(lambda _, b=button: self.on_result_clicked(b))
                button.on_icon_clicked(lambda _, b=button: self.clear_result(b.query_id))
                
                # Add button to layout (insert at top, after removing stretch)
                self.buttons_layout.removeItem(self.buttons_layout.itemAt(self.buttons_layout.count() - 1))  # Remove stretch
                self.buttons_layout.addWidget(button)  
                self.buttons_layout.addStretch()  # Add stretch back
                
                # Add to tracking list
                self.query_buttons.append(button)

        if self.query_counter != 0:
            self.clear_button.setEnabled(True)
                 
    def on_result_clicked(self, clicked_button):
        """Handle result button click"""
        self.select_button(clicked_button)
        self.result_clicked.emit(f"{self.results_directory}/{clicked_button.query_id}")
    
    def select_button(self, selected_button):
        """Select a button and deselect others"""
        self.curr_button = selected_button
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
                button.setParent(None)
                # Try to delete the associated file
                dir = f"history/databases/{self.db_name}/query_results"
                for filename in os.listdir(dir):
                    file_path = os.path.join(dir, filename)
                    shutil.rmtree(file_path)
            
            self.query_buttons.clear()
            self.query_counter = 0
            
            # Show empty label again
            self.empty_label.show()
            self.clear_button.setEnabled(False)
            
            # Clear main content
            self.result_clicked.emit("")

    def clear_result(self, query_id):
        """Clear current query results"""
        reply = QMessageBox.question(
            self, 
            'Clear Results', 
            'Are you sure you want to clear query results?\nThis will delete saved result files.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove button
            for i, b in enumerate(self.query_buttons):
                if b.query_id == query_id:
                    button = self.query_buttons.pop(i)
                    button.deleteLater()
                    button.setParent(None)
                    self.buttons_layout.removeWidget(button)
                    break
            # Try to delete the associated file
            dir = f"history/databases/{self.db_name}/query_results/{query_id}"
            shutil.rmtree(dir)
            
            if query_id == self.query_counter:
                self.query_counter -= 1

            # Show empty label if all deleted
            if self.query_counter == 0:
                self.empty_label.show()
                self.clear_button.setEnabled(False)
            
            # Clear main content if its the current button
            if self.curr_button.query_id == query_id:
                self.result_clicked.emit("")
                self.clear_checked()

    def changeDatabase(self):
        file_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption="(.sqlite) اختر قاعدة بياناتك",
            filter="SQLite Database Files (*.sqlite);;All Files (*)"
        )
        
        self.db_changed.emit(file_path)

    def clear_checked(self):
        self.curr_button = None
        for button in self.query_buttons:
            button.setChecked(False)        