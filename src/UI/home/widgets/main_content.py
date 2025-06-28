import json
import os
import csv

from UI.home.widgets.textbox import TextBox
from UI.home.widgets.plot_widget import PlotWidget

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QFileDialog, QWidget, QScrollArea,
    QDialog, QTableWidget, QTableWidgetItem, QAbstractItemView, QApplication, QLineEdit, QMessageBox
)                         
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon


class MainContent(QFrame):
    """Main content area of the main window"""
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
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)
        
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
        self.main_layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Description
        self.description_label = QLabel("اكتب سؤال عن ما تريد معرفته عن بياناتك")
        self.description_label.setStyleSheet("""
            QLabel {
                color: #64748B;
                font-size: 14px;
                margin-bottom: 10px;
            }
        """)
        self.main_layout.addWidget(self.description_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
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
        self.main_layout.addWidget(self.textbox_label)
        # Text box
        self.text_input = TextBox(self.db_manager)
        self.main_layout.addWidget(self.text_input)
        
        # Additional action buttons
        button_layout = QHBoxLayout()

        # New question button
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

        # Show code button
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
        
        self.main_layout.addLayout(button_layout)
        
        # Plots label 
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
        self.main_layout.addWidget(self.plots_label)
        
        # Plots
        self.plots_area = QScrollArea()
        self.plots_area.setFixedHeight(200)
        self.plots_area.setWidgetResizable(True)
        self.plots_area.setContentsMargins(0, 0, 0, 0)
        self.plots_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.plots_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.plots_container = QWidget()
        self.plots_layout = QHBoxLayout(self.plots_container)
        self.plots_area.setWidget(self.plots_container)
        self.main_layout.addWidget(self.plots_area)

        # Placeholder for plots when there are no plots generated
        self.plots_empty = QLineEdit()
        self.plots_empty.setReadOnly(True)
        self.plots_empty.setPlaceholderText("لم يتم انتاج اي رسومات لهذا السؤال")
        self.plots_empty.setStyleSheet("""
            QLineEdit {
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
        self.main_layout.addWidget(self.plots_empty)

        # Results area
        self.results_layout = QHBoxLayout()
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
        self.results_layout.addWidget(self.results_label)
        self.results_layout.addStretch()

        # Export to CSV button
        self.export_button = QPushButton(icon=QIcon('src/UI/assets/download.png'))
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #6B7280;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
            QPushButton:pressed {
                background-color: #374151;
            }
        """)
        self.export_button.clicked.connect(self.export_to_csv)
        self.results_layout.addWidget(self.export_button)
        self.main_layout.addLayout(self.results_layout)

        # Data table
        self.results_area = QTableWidget()
        self.results_area.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.main_layout.addWidget(self.results_area)
        self.main_layout.addStretch()
        
        self.setLayout(self.main_layout)
    
    def update_ui(self, initial):
        """Updates UI depending if its the home page or the results page"""
        self.initial = initial

        if self.initial:
            self.main_layout.insertStretch(0)
            self.main_layout.insertStretch(self.main_layout.count() - 1)

            self.plots_area.hide()
            self.plots_label.hide()
            self.plots_empty.hide()

            self.results_area.hide()
            self.results_label.hide()
            self.export_button.hide()

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
            self.main_layout.removeItem(self.main_layout.itemAt(0))
            self.main_layout.removeItem(self.main_layout.itemAt(self.main_layout.count() - 1))

            self.plots_label.show()

            self.results_area.show()
            self.results_label.show()
            self.export_button.show()

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

        # Buttons
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

        button_layout.addWidget(copy_button)
        button_layout.addWidget(ok_button)

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
        if not folder_path:  # Empty path means go to home page
            self.initial = True
            self.update_ui(self.initial)
            return

        has_plots = False
        for f in os.listdir(folder_path):
            path = os.path.join(folder_path, f)

            if os.path.isfile(path): # Load results
                with open(path, 'r', encoding='utf-8') as f:
                    result = json.load(f)
            else: # Load plots
                while self.plots_layout.count():
                    item = self.plots_layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.deleteLater()
                self.plots_layout.addStretch()

                for plot in os.listdir(path):
                    plot_path = os.path.join(path, plot)
                    plot_widget = PlotWidget(plot_path, QSize(150, 150))
                    plot_widget.setStyleSheet("""
                        margin: 0 10px;
                    """)
                    self.plots_layout.addWidget(plot_widget)
                    has_plots = True
                self.plots_layout.addStretch()
                
                self.plots_area.setWidget(self.plots_container)

        if has_plots: # Remove plots placeholder
            self.plots_empty.hide()
            self.plots_area.show()
        else: # Show plots placeholder
            self.plots_area.hide()
            self.plots_empty.show()

        if self.initial == True:
            self.initial = False
            self.update_ui(self.initial)
        
        # Display the loaded result
        self.columns = result['columns']
        self.rows = result['rows']
        self.results_area.setColumnCount(len(self.columns))
        self.results_area.setHorizontalHeaderLabels(self.columns)
        row_count = min(len(self.rows), 100)
        self.results_area.setRowCount(row_count)
        for i, row in enumerate(self.rows[:row_count]):
            for j, value in enumerate(row):
                self.results_area.setItem(i, j, QTableWidgetItem("NULL" if value is None else str(value)))

        # load the question back into the editor
        self.text_input.text_edit.setText(result['query_text'])

        # load SQL Code
        self.sql_code = result['query_sql']
        
    def on_new_question_pressed(self):
        """Updates UI to the home page when pressed"""
        self.update_ui(initial=True)
        self.new_question.emit()

    def export_to_csv(self):
        """Exports current data loaded to a csv file"""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSV",
            "results.csv",
            "CSV files (*.csv);;All files (*)"
        )

        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(self.columns)  # Write header
                    writer.writerows(self.rows)    # Write all data rows

                QMessageBox.information(self, "Export Successful", f"Results saved to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"An error occurred:\n{e}")
