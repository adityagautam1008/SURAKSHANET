from PySide6.QtWidgets import *
from PySide6.QtGui import *
import shutil, os
from database import conn, cur

class MissingForm(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Report Missing Person")
        self.setMinimumWidth(400)

        layout = QFormLayout(self)

        self.name = QLineEdit()
        self.age = QLineEdit()
        self.gender = QComboBox()
        self.gender.addItems(["Male","Female","Other"])
        self.last_seen = QLineEdit()
        self.desc = QTextEdit()
        self.reporter = QLineEdit()
        self.phone = QLineEdit()

        self.photo_path = ""
        btn_photo = QPushButton("Upload Photo")
        btn_photo.clicked.connect(self.upload_photo)

        submit = QPushButton("Submit Report")
        submit.clicked.connect(self.save_data)

        layout.addRow("Name:",self.name)
        layout.addRow("Age:",self.age)
        layout.addRow("Gender:",self.gender)
        layout.addRow("Last Seen Location:",self.last_seen)
        layout.addRow("Description:",self.desc)
        layout.addRow("Reporter Name:",self.reporter)
        layout.addRow("Phone:",self.phone)
        layout.addRow(btn_photo)
        layout.addRow(submit)

    def upload_photo(self):
        file,_ = QFileDialog.getOpenFileName(self,"Select Photo","","Images (*.png *.jpg *.jpeg)")
        if file:
            self.photo_path = file

    def save_data(self):
        if not self.name.text():
            QMessageBox.warning(self,"Error","Name required")
            return

        photo_dest=""
        if self.photo_path:
            os.makedirs("data/photos",exist_ok=True)
            photo_dest=f"data/photos/{os.path.basename(self.photo_path)}"
            shutil.copy(self.photo_path,photo_dest)

        cur.execute("""
        INSERT INTO missing_persons(name,age,gender,last_seen,description,photo,reporter,phone)
        VALUES(?,?,?,?,?,?,?,?)
        """,(
            self.name.text(),
            self.age.text(),
            self.gender.currentText(),
            self.last_seen.text(),
            self.desc.toPlainText(),
            photo_dest,
            self.reporter.text(),
            self.phone.text()
        ))

        conn.commit()
        QMessageBox.information(self,"Saved","Report Stored Successfully")
        self.close()