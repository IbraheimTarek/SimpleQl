from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSizePolicy, QSpacerItem,
    QHBoxLayout, QProgressBar, QFileDialog
)
from PyQt6.QtCore import Qt, QSize, QTimer, QEvent, QPropertyAnimation, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap

from UI.initial_page.widgets.image import ImageWidget
from UI.initial_page.widgets.animated_button import AnimatedButton

from database_manager import DBManager


class InitialPage(QWidget):

    connected = pyqtSignal(str) # Signal to know when app finish connecting to database

    def __init__(self):
        super().__init__()

        self.setWindowTitle("SimpleQL")
        self.setMinimumSize(800, 600)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.outer_layout = QVBoxLayout(self)

        # Container widget
        self.container = QWidget()
        self.container.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 20px;
                padding: 30px;
            }
        """)
        layout = QVBoxLayout(self.container)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Logo
        image = ImageWidget('src/UI/assets/GP_logo.png', max_size=QSize(400, 200))
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image)

        # Title
        title = QLabel("SimpleQL اهلا بك في")
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Connect to DB Button
        button_container = QWidget()
        button_container.setFixedHeight(60)
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.button = AnimatedButton("  اتصل بقاعدة بياناتك", icon=QIcon(QPixmap('src/UI/assets/database.png')))
        self.button.clicked.connect(self.start_process)

        button_layout.addStretch()
        button_layout.addWidget(self.button, alignment=Qt.AlignmentFlag.AlignCenter)
        button_layout.addStretch()
        layout.addWidget(button_container)

        # Progress Bar and Status
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: grey; font-size: 14px;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #eee;
                border-radius: 5px;
                padding: 0;
                margin: 0;
            }
            QProgressBar::chunk {
                background-color: #94E8F0;
                border-radius: 5px;
                padding: 0;
                margin: 0;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.progress_anim = QPropertyAnimation(self.progress_bar, b"value")
        self.progress_anim.setDuration(1000)  

        # Hint Paragraph
        self.paragraph = QLabel("هل انت مستعد لاكتشاف بياناتك؟ اضغط الزر اعلاه للبدأ")
        self.paragraph.setWordWrap(True)
        self.paragraph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.paragraph.setStyleSheet("QLabel { color: grey; padding: 0;}")
        layout.addWidget(self.paragraph)

        self.outer_layout.addWidget(self.container)

        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # Connecting to DB steps, some of them are just for fancy loading
        self.steps = [
            ("يتم الاتصال بقاعدة البيانات...", self.step1),
            ("يتم عمل بيتزا...", self.step2),
            ("يتم لعب ليج...", self.step3),
            ("اللمسات الاخيرة...", self.step4)
        ]
        self.current_step = 0

    def start_process(self):
        """
        Starts the process of connecting to the selected database
        """
        # Open a window to prompt the user to select a DB
        file_path, _ = QFileDialog.getOpenFileName(
            parent=self,
            caption="اختر بياناتك (.sql)",
            filter="SQLite Database Files (*.sqlite);;All Files (*)"
        )

        if file_path:
            self.db_path = file_path

            # Disable button
            self.button.setEnabled(False)
            self.button.anim_enabled = False
            self.button.setStyleSheet(self.button.styleSheet() + "opacity: 0.5;")

            # Show progress bar and update status
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            self.status_label.setText("Starting...")

            self.paragraph.setVisible(False)

            self.current_step = 0
            self.failed = False 

            self.run_next_step()

    def set_progress_value(self, value):
        """
        Sets the value of the progress bar and updates its animation.
        """
        self.progress_anim.stop()
        self.progress_anim.setStartValue(self.progress_bar.value())
        self.progress_anim.setEndValue(value)
        self.progress_anim.start()

    def run_next_step(self):
        """
        Runs next step's function
        """

        if self.failed: # connecting to DB failed
            self.status_label.setText("لقد تعذر الاتصال. الرجاء حاول مرة اخري")
            # Stop animation
            self.progress_anim.stop()
            self.progress_anim.setStartValue(self.progress_bar.value())
            self.set_progress_value(0)
            self.progress_anim.setDuration(200)
            self.progress_anim.start()
            # Enable button
            self.button.setEnabled(True)
            self.button.anim_enabled = True
            # a dummy event to reset the animation of button
            dummy_event = QEvent(QEvent.Type.Leave)
            self.button.leaveEvent(dummy_event)
            self.button.setStyleSheet(self.button.styleSheet().replace("opacity: 0.5;", ""))
            return

        if self.current_step >= len(self.steps): # All steps finished
            self.status_label.setText("Connected successfully.")
            self.set_progress_value(100)
            self.progress_anim.finished.connect(self.on_progress_complete)
            return

        # Run the next step
        label, func = self.steps[self.current_step]
        self.status_label.setText(label)

        func(self.finish_step)

    def finish_step(self):
        self.current_step += 1
        progress = int((self.current_step / len(self.steps)) * 100)
        self.set_progress_value(progress)
        self.run_next_step()

    def on_progress_complete(self):
        # Prevent multiple calls if signal fires more than once
        self.progress_anim.finished.disconnect(self.on_progress_complete)
        self.connected.emit(self.db_path)
        self.close()

    # for fancy loading
    def step1(self, done_callback):
        QTimer.singleShot(500, done_callback)

    def step2(self, done_callback):
        self.db_manager = DBManager(self.db_path)
        QTimer.singleShot(700, done_callback)

    # for fancy loading
    def step3(self, done_callback):
        QTimer.singleShot(300, done_callback)

    # for fancy loading
    def step4(self, done_callback):
        QTimer.singleShot(100, done_callback)
        