import json
import os
from UI.home.widgets.textbox import TextBox
from UI.home.widgets.plot_widget import PlotWidget

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QTextEdit, QWidget, QScrollArea,
    QDialog, QTableWidget, QTableWidgetItem, QAbstractItemView, QApplication
)                         
from PyQt6.QtCore import Qt, pyqtSignal, QSize


class MainContent(QFrame):
    """Main content area with textbox and label"""
    new_question = pyqtSignal()

    def __init__(self, db_manager, initial : bool, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.initial = initial
        self.init_ui()
        self.update_ui(initial)
        
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
        layout.addStretch()
        
        # Title area
        self.title_label = QLabel("كيف يمكنني مساعدتك؟")
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
        self.description_label = QLabel("اكتب سؤال عن ما تريد معرفته عن بياناتك")
        self.description_label.setStyleSheet("""
            QLabel {
                color: #64748B;
                font-size: 14px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(self.description_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Text input area
        self.textbox_label = QLabel("السؤال")
        self.textbox_label.setStyleSheet("""
            QLabel {
                color: #374151;
                font-size: 16px;
                font-weight: bold;
                margin-top: 20px;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(self.textbox_label)
        # Integrated text input with execute button
        self.text_input = TextBox(self.db_manager)
        layout.addWidget(self.text_input)
        
        # Additional action buttons
        button_layout = QHBoxLayout()

        self.new_button = QPushButton("سؤال جديد")
        self.new_button.setStyleSheet("""
            QPushButton {
                background-color: #14B8A6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0F766E;
            }
            QPushButton:pressed {
                background-color: #0D5B56;
            }
        """)
        self.new_button.clicked.connect(self.on_new_question_pressed)

        self.sql_button = QPushButton("اظهر الكود") 
        self.sql_button.setStyleSheet("""
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
        self.sql_button.clicked.connect(self.show_sql_code)
        
        button_layout.addStretch()
        button_layout.addWidget(self.sql_button)
        button_layout.addWidget(self.new_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Plot area placeholder
        self.plots_label = QLabel("الرسومات البيانية")
        self.plots_label.setStyleSheet("""
            QLabel {
                color: #374151;
                font-size: 16px;
                font-weight: bold;
                margin-top: 20px;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(self.plots_label)
        
        # plots
        self.plots_area = QScrollArea()
        self.plots_area.setWidgetResizable(True)
        self.plots_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.plots_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.plots_area.setFixedHeight(250)
        self.plots_container = QWidget()
        self.plots_layout = QHBoxLayout(self.plots_container)
        self.plots_area.setWidget(self.plots_container)
        layout.addWidget(self.plots_area)

        self.plots_empty = QTextEdit()
        self.plots_empty.setReadOnly(True)
        self.plots_empty.setPlaceholderText("لم يتم انتاج اي رسومات لهذا السؤال")
        self.plots_empty.setStyleSheet("""
            QTextEdit {
                border: 2px solid #E5E7EB;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                font-weight: bold;
                background-color: #F9FAFB;
                color: #1F2937;
            }
        """)
        self.plots_empty.setMinimumHeight(150)
        layout.addWidget(self.plots_empty)

        # Results area
        self.results_label = QLabel("البيانات الناتجة")
        self.results_label.setStyleSheet("""
            QLabel {
                color: #374151;
                font-size: 16px;
                font-weight: bold;
                margin-top: 20px;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(self.results_label)
        self.results_area = QTableWidget()
        self.results_area.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.results_area)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def update_ui(self, initial):
        self.initial = initial

        if self.initial:
            self.plots_area.hide()
            self.plots_label.hide()
            self.plots_empty.hide()

            self.results_area.hide()
            self.results_label.hide()

            self.textbox_label.hide()

            self.sql_button.hide()
            self.new_button.hide()

            self.title_label.show()
            self.description_label.show()

            self.text_input.execute_button.show()
            self.text_input.text_edit.setReadOnly(False)

            self.results_area.clear()
            self.text_input.text_edit.clear()
        else:
            self.plots_area.show()
            self.plots_label.show()
            self.plots_empty.show()


            self.results_area.show()
            self.results_label.show()

            self.textbox_label.show()

            self.sql_button.show()
            self.new_button.show()
        
            self.title_label.hide()
            self.description_label.hide()

            self.text_input.execute_button.hide()
            self.text_input.text_edit.setReadOnly(True)

    def show_sql_code(self):
        """Show SQL Code to the user"""
        dialog = QDialog()
        dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        # Container layout
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Text label
        label = QLabel(self.sql_code)
        label.setWordWrap(True)
        label.setStyleSheet("""
            QLabel {
                color: #1E293B;
                font-size: 14px;
                font-weight: 500;
            }
        """)

        # Button layout (OK + Copy)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        # OK button
        ok_button = QPushButton("OK")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #14B8A6;
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #0D9488;
            }
            QPushButton:pressed {
                background-color: #0F766E;
            }
        """)
        ok_button.clicked.connect(dialog.accept)

        # Copy button
        copy_button = QPushButton("نسخ")
        copy_button.setStyleSheet("""
            QPushButton {
                background-color: #6B7280;
                color: white;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
            QPushButton:pressed {
                background-color: #374151;
            }
        """)
        def copy_tp_clipboard():
            QApplication.clipboard().setText(self.sql_code)
            copy_button.setText('تم النسخ')
        copy_button.clicked.connect(copy_tp_clipboard)

        # Add buttons to layout
        button_layout.addWidget(copy_button)
        button_layout.addWidget(ok_button)

        # Add widgets to main layout
        layout.addWidget(label)
        layout.addLayout(button_layout)

        # Set white background and border
        dialog.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                border: 2px solid #14B8A6;
                border-radius: 12px;
            }
        """)

        dialog.exec()
    
    def load_result_from_file(self, folder_path):
        """Load and display result from file"""
        if not folder_path:  # Empty path means clear all results and go to initial state
            self.initial = True
            self.update_ui(self.initial)
            return
            
        self.initial = False
        self.update_ui(self.initial)
        has_plots = False
        for f in os.listdir(folder_path):
            path = os.path.join(folder_path, f)
            if os.path.isfile(path):
                # Load results
                print(f"File: {path}")
                with open(path, 'r', encoding='utf-8') as f:
                    result = json.load(f)
            else:
                # Load plots
                print(f"Directory : {path}")
                self.plots_layout.addStretch()
                for plot in os.listdir(path):
                    plot_path = os.path.join(path, plot)
                    print(f"Plot: {plot_path}")
                    plot_widget = PlotWidget(plot_path, QSize(200, 200))
                    plot_widget.setStyleSheet("""
                        margin: 0 10px;
                    """)
                    self.plots_layout.addWidget(plot_widget)
                    has_plots = True
                self.plots_layout.addStretch()

        if has_plots:
            self.plots_area.show()
            self.plots_empty.hide()
        else:
            self.plots_area.hide()
            self.plots_empty.show()
        
        # Display the loaded result
        columns = result['columns']
        rows = result['rows']
        self.results_area.setColumnCount(len(columns))
        self.results_area.setHorizontalHeaderLabels(columns)
        row_count = min(len(rows), 100)
        self.results_area.setRowCount(row_count)
        for i, row in enumerate(rows[:row_count]):
            for j, value in enumerate(row):
                self.results_area.setItem(i, j, QTableWidgetItem("NULL" if value is None else str(value)))

        # load the query back into the editor
        self.text_input.text_edit.setText(result['query_text'])

        # load SQL Code
        self.sql_code = result['query_sql']
        
    def on_new_question_pressed(self):
        self.update_ui(initial=True)
        self.new_question.emit()
