from PyQt6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QLabel, QLineEdit, 
    QScrollArea, QGroupBox, QHBoxLayout, QDialog
)

from pipeline.translator.Translator import translate

class SchemaViewer(QDialog):
    """
    Window for editing database schema descriptions
    Args:
        db_manager (DBManager): Manager for current database
    """
    def __init__(self, db_manager: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تفاصيل قاعدة البيانات")
        self.setMinimumSize(800, 600)
        self.db_manager = db_manager
        self.schema_data = db_manager.schema
        self.description_inputs = {}  # Stores inputs for saving later

        # Main layout
        layout = QVBoxLayout(self)

        # Scroll area for descriptions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # For each table make a groupbox
        for table_name, columns in self.schema_data.items():
            group = QGroupBox(table_name)
            group.setStyleSheet("""
                QGroupBox { 
                    border: 2px solid #14B8A6;
                    border-radius: 6px;
                    padding: 10px 5px;
                    margin-bottom: 10px;     
                    font-weight: bold;
                    font-size: 14px;            
                }
                QGroupBox::title {
                    subcontrol-position: top left; 
                    color: #14B8A6; 
                }
            """)
            group_layout = QVBoxLayout()

            for column_name, description in columns.items():
                row = QHBoxLayout()

                column_label = QLabel(column_name)
                column_label.setFixedWidth(120)

                input_field = QLineEdit(description)
                self.description_inputs[(table_name, column_name)] = input_field

                row.addWidget(column_label)
                row.addWidget(input_field)
                group_layout.addLayout(row)

            group.setLayout(group_layout)
            scroll_layout.addWidget(group)

        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)

        layout.addWidget(scroll)

        # Save button
        save_btn = QPushButton("احفظ")
        save_btn.setStyleSheet("""
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
        save_btn.clicked.connect(self.save_descriptions)
        layout.addWidget(save_btn)

    def save_descriptions(self):
        """Saves all descriptions when save button is pressed"""
        for (table, column), input_field in self.description_inputs.items():
            desc = input_field.text()
            self.schema_data[table][column] = desc
            if desc == "":
                continue
            translated_desc = translate(desc)
            self.db_manager.embedDescription(table, column, translated_desc)
        self.db_manager.save()
        self.accept()
