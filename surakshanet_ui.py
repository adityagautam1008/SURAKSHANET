# ====================== SURAKSHANET COMPLETE SYSTEM ======================
import sys, os, shutil, sqlite3, cv2, numpy as np
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *

os.makedirs("data/photos", exist_ok=True)

# ---------------- DATABASE ----------------
conn = sqlite3.connect("suraksha.db")
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS missing_persons(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT, age TEXT, gender TEXT,
last_seen TEXT, description TEXT,
photo TEXT, reporter TEXT, phone TEXT)""")

cur.execute("""CREATE TABLE IF NOT EXISTS match_log(
id INTEGER PRIMARY KEY AUTOINCREMENT,
person_name TEXT, phone TEXT,
time TEXT, confidence REAL)""")

conn.commit()

# ---------------- FACE VALIDATION ----------------
def validate_face_image(path):
    detector=cv2.FaceDetectorYN.create("models/face_detection_yunet_2023mar.onnx","",(320,320))
    img=cv2.imread(path)
    if img is None: return False
    h,w,_=img.shape
    detector.setInputSize((w,h))
    _,faces=detector.detect(img)
    return faces is not None

# =========================================================
# ---------------- REGISTER FORM --------------------------
# =========================================================
class MissingForm(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Report Missing Person")
        layout=QFormLayout(self)

        self.name=QLineEdit()
        self.age=QLineEdit()
        self.gender=QComboBox(); self.gender.addItems(["Male","Female","Other"])
        self.last_seen=QLineEdit()
        self.desc=QTextEdit()
        self.reporter=QLineEdit()
        self.phone=QLineEdit()
        self.photo=""

        btn=QPushButton("Upload Photo"); btn.clicked.connect(self.upload)
        save=QPushButton("Submit Report"); save.clicked.connect(self.store)

        layout.addRow("Name:",self.name)
        layout.addRow("Age:",self.age)
        layout.addRow("Gender:",self.gender)
        layout.addRow("Last Seen:",self.last_seen)
        layout.addRow("Description:",self.desc)
        layout.addRow("Reporter:",self.reporter)
        layout.addRow("Phone:",self.phone)
        layout.addRow(btn); layout.addRow(save)

    def upload(self):
        f,_=QFileDialog.getOpenFileName(self,"Select Photo","","Images (*.jpg *.png)")
        if not f: return
        if not validate_face_image(f):
            QMessageBox.warning(self,"Invalid Photo","Clear front face required")
            return
        self.photo=f

    def store(self):
        if not self.name.text(): return
        dest=""
        if self.photo:
            dest="data/photos/"+os.path.basename(self.photo)
            shutil.copy(self.photo,dest)

        cur.execute("""INSERT INTO missing_persons(name,age,gender,last_seen,description,photo,reporter,phone)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (self.name.text(),self.age.text(),self.gender.currentText(),
                     self.last_seen.text(),self.desc.toPlainText(),dest,
                     self.reporter.text(),self.phone.text()))
        conn.commit()
        QMessageBox.information(self,"Saved","Record stored")
        self.close()

# =========================================================
# ---------------- SEARCH WINDOW --------------------------
# =========================================================
class SearchWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Search Missing Persons")
        self.resize(600,500)

        layout=QVBoxLayout(self)
        self.box=QLineEdit()
        self.box.setPlaceholderText("Type name...")
        self.box.textChanged.connect(self.load)
        layout.addWidget(self.box)

        self.list=QListWidget()
        layout.addWidget(self.list)
        self.load()

    def load(self):
        self.list.clear()
        t=self.box.text()
        cur.execute("SELECT name,last_seen,phone FROM missing_persons WHERE name LIKE ?",(f"%{t}%",))
        for n,l,p in cur.fetchall():
            self.list.addItem(f"{n} | Last seen: {l} | Phone: {p}")

# =========================================================
# ---------------- FACE RECOGNITION -----------------------
# =========================================================
class FaceScanner(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Face Scan")
        QLabel("Look at camera & stay still",self).move(40,40)
        QTimer.singleShot(400,self.start)

    def load_models(self):
        self.detector=cv2.FaceDetectorYN.create("models/face_detection_yunet_2023mar.onnx","",(320,320))
        self.recognizer=cv2.FaceRecognizerSF.create("models/face_recognition_sface_2021dec.onnx","")

    def normalize(self,e):
        e=e.flatten()
        return e/np.linalg.norm(e)

    def embedding(self,img):
        h,w,_=img.shape
        self.detector.setInputSize((w,h))
        _,faces=self.detector.detect(img)
        if faces is None: return None
        if faces[0][2]<90: return None
        aligned=self.recognizer.alignCrop(img,faces[0])
        emb=self.recognizer.feature(aligned).flatten()
        return self.normalize(emb)

    def load_db(self):
        db=[]
        cur.execute("SELECT name,photo,phone FROM missing_persons")
        for n,p,ph in cur.fetchall():
            if p and os.path.exists(p):
                e=self.embedding(cv2.imread(p))
                if e is not None:
                    db.append((n,ph,e))
        return db

    def capture(self,cap):
        samples=[]
        for _ in range(6):
            r,f=cap.read()
            if not r: continue
            e=self.embedding(f)
            if e is not None: samples.append(e)
            cv2.imshow("Scanning...",f); cv2.waitKey(250)
        if len(samples)<3: return None
        return self.normalize(np.mean(samples,axis=0))

    def start(self):
        self.load_models()
        db=self.load_db()
        if not db:
            QMessageBox.warning(self,"No Data","Add persons first")
            self.close(); return

        cap=cv2.VideoCapture(0)
        emb=self.capture(cap)
        cap.release(); cv2.destroyAllWindows()

        if emb is None:
            QMessageBox.warning(self,"Failed","Face unclear")
            self.close(); return

        best=None;score=0
        for n,ph,e in db:
            s=float(np.dot(emb,e))
            if s>score: score=s;best=(n,ph)

        if score>0.50:
            QMessageBox.information(self,"MATCH FOUND",f"{best[0]}\nPhone: {best[1]}\nConfidence: {round(score*100,1)}%")
            cur.execute("INSERT INTO match_log(person_name,phone,time,confidence) VALUES(?,?,datetime('now'),?)",(best[0],best[1],score))
            conn.commit()
        else:
            QMessageBox.information(self,"No Match",f"Similarity: {round(score*100,1)}%")

        self.close()

# =========================================================
# ---------------- STATS WINDOW ---------------------------
# =========================================================
class StatsWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Statistics")
        layout=QVBoxLayout(self)

        cur.execute("SELECT COUNT(*) FROM missing_persons")
        missing=cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM match_log")
        matched=cur.fetchone()[0]

        layout.addWidget(QLabel(f"Total Missing Persons: {missing}"))
        layout.addWidget(QLabel(f"Total Matches Found: {matched}"))

# =========================================================
# ---------------- MAIN WINDOW ----------------------------
# =========================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SurakshaNet Rescue System")
        self.resize(1000,500)

        w=QWidget(); self.setCentralWidget(w)
        g=QGridLayout(w)

        title=QLabel("SURAKSHA NET CONTROL PANEL")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:24px;font-weight:bold")
        g.addWidget(title,0,0,1,4)

        buttons=[
            ("Report Missing",self.missing),
            ("Scan Found Person",self.scan),
            ("Search Database",self.search),
            ("Statistics",self.stats)
        ]

        for i,(t,f) in enumerate(buttons):
            b=QPushButton(t)
            b.setMinimumHeight(120)
            b.clicked.connect(f)
            g.addWidget(b,1,i)

    def missing(self): MissingForm().exec()
    def scan(self): FaceScanner().exec()
    def search(self): SearchWindow().exec()
    def stats(self): StatsWindow().exec()

# =========================================================
app=QApplication(sys.argv)
win=MainWindow()
win.show()
app.exec()