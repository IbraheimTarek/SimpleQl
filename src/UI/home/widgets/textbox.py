from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QTextEdit, QMessageBox, QWidget
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QMovie

from run_pipeline import run_pipeline

class Worker(QObject):
    finished = pyqtSignal()
    result = pyqtSignal(str, str, list, list)

    def __init__(self, db_manager, query_text):
        super().__init__()
        self.db_manager = db_manager
        self.query_text = query_text
        self.running = False

    def run(self):
        if self.running:
            return
        self.running = True

        query_sql, rows, columns = run_pipeline(self.query_text, self.db_manager)
        if query_sql and rows and columns:
            self.result.emit(self.query_text, query_sql, rows, columns)

        self.running = False
        self.finished.emit()

class TextBox(QFrame):
    query_executed = pyqtSignal(str, str, list, list)  # query_text, query_sql, rows, columns

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.max_lines = 3
        self.min_lines = 1
        self.line_height = 17
        self.base_height = 36
        self.init_ui()

    def init_ui(self):
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

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(8)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("ما هو عدد العملاء اصحاب المرتبات الاكبر من 5 الاف؟")
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

        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

        self.set_height_for_lines(self.min_lines)
        self.text_edit.textChanged.connect(self.on_text_changed)

        # Execute button with spinner
        self.execute_button = QPushButton("▶")
        self.execute_button.setFixedSize(36, 36)
        self.execute_button.setToolTip("تنفيذ السؤال")
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
        self.execute_button.setEnabled(False)

        button_container = QFrame()
        button_container.setStyleSheet("""
            border: none;
        """)
        button_layout = QVBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addStretch()
        button_layout.addWidget(self.execute_button)
        button_layout.addStretch()
        button_container.setLayout(button_layout)

        main_layout.addWidget(self.text_edit, 1)
        main_layout.addWidget(button_container)

        self.spinner = QMovie("src/UI/assets/spinner.gif")
        self.spinner.setScaledSize(self.execute_button.size()* 0.8)

        self.setLayout(main_layout)
        self.text_edit.setFocus()

    def set_height_for_lines(self, lines):
        height = self.base_height + (self.line_height * lines)
        self.setFixedHeight(int(height))

    def on_text_changed(self):
        text = self.text_edit.toPlainText().strip()
        if not hasattr(self, "worker") or not self.worker or not self.worker.running:
            self.execute_button.setEnabled(bool(text))

        doc = self.text_edit.document()
        doc_height = doc.size().height()
        lines_needed = max(1, int(doc_height / self.line_height)) if self.line_height > 0 else 1
        display_lines = min(lines_needed, self.max_lines)
        self.set_height_for_lines(display_lines)

        self.text_edit.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded if lines_needed > self.max_lines else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

    def execute_query(self):
        query = self.text_edit.toPlainText().strip()
        if not query:
            return

        # Disable button and show spinner
        self.execute_button.setEnabled(False)
        self.execute_button.setText("")
        self.execute_button.setIconSize(self.spinner.scaledSize())
        self.spinner.frameChanged.connect(lambda: self.execute_button.setIcon(QIcon(self.spinner.currentPixmap())))
        self.spinner.start()

        # Run long task in background
        self.thread = QThread()
        self.worker = Worker(self.db_manager, query)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.result.connect(self.on_query_executed)
        try:
            self.thread.start()
        except:
            msg = QMessageBox.critical(
                self, 
                "خطأ", 
                "تعذر انتاج الكود المناسب لهذا السؤال. الرجاء تحسين السؤال او حاول مرة اخري", 
                QMessageBox.StandardButton.Ok
            )
            self.spinner.stop()
            self.execute_button.setIcon(QIcon())
            self.execute_button.setText("▶")
            self.execute_button.setEnabled(True)
            self.worker.running = False

            # When user clicks OK, stop the thread (if running)
            if self.thread.isRunning():
                msg.buttonClicked.connect(self.thread.quit)

    @pyqtSlot(str, str, list, list)
    def on_query_executed(self, query_text, query_sql, rows, columns):
        # Restore button
        self.spinner.stop()
        self.execute_button.setIcon(QIcon())
        self.execute_button.setText("▶")
        self.execute_button.setEnabled(True)

        # Emit signal
        self.query_executed.emit(query_text, query_sql, rows, columns)

    def get_text(self):
        return self.text_edit.toPlainText()

    def set_text(self, text):
        self.text_edit.setText(text)

    def clear(self):
        self.text_edit.clear()

    def set_placeholder_text(self, text):
        self.text_edit.setPlaceholderText(text)
