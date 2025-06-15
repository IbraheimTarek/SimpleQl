from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout


app = QApplication([])

window = QWidget()
label = QLabel("<p style='color:blue;font-size:46px;'>Hello</p>")
button1 = QPushButton("Hello mf1")
button1.setStyleSheet("""
    QPushButton {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 10px;
        border-radius: 8px;
        font-size: 16px;
    }
    QPushButton:hover {
        background-color: #45a049;
    }
    QPushButton:pressed {
        background-color: #397d3c;
    }
""")

button1.setStyle()

button2 = QPushButton("Hello mf2")
button2.setStyleSheet('''
    QPushButton {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 10px;
        border-radius: 8px;
        font-size: 16px;
    }
    
    QPushButton:hover {
        background-color: #45a049;
    }
    QPushButton:pressed {
        background-color: #397d3c;
    }
''')

layout = QVBoxLayout(window)
layout.addWidget(label)
layout.addWidget(button1)
layout.addWidget(button2)
window.show() 


# Start the event loop.
app.exec()