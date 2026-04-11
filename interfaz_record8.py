import sys
import time
import os
import json
import serial
from collections import deque

from openai import OpenAI

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

PORT = "COM4"
BAUD = 115200

USER_HOME = os.path.expanduser("~")
BASE_PATH = os.path.join(USER_HOME, "Desktop", "R-One", "secuencias")
os.makedirs(BASE_PATH, exist_ok=True)

# ================= TEMA =================
def aplicar_tema(app):
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(235, 240, 255))
    palette.setColor(QPalette.WindowText, Qt.black)
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, Qt.black)
    palette.setColor(QPalette.Button, QColor(210, 220, 255))
    palette.setColor(QPalette.ButtonText, Qt.black)
    palette.setColor(QPalette.Highlight, QColor(140, 170, 255))
    palette.setColor(QPalette.HighlightedText, Qt.white)

    app.setPalette(palette)

# ================= BOTONES =================
def estilo_boton(boton, color):
    boton.setStyleSheet(f"""
        QPushButton {{
            background-color: {color};
            border-radius: 10px;
            padding: 8px;
            color: black;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #d0d8ff;
        }}
    """)
    boton.setFixedHeight(42)

# ================= IA =================
def generar_movimiento_ia(texto):
    prompt = f"""
Eres un sistema de control de robot humanoide.
Convierte este texto en una lista JSON de movimientos.
Formato:
[
{{"pca":0,"servo":0,"pos":500,"vel":5,"t":0}}
]
Reglas:
- pos: 0 a 1000
- vel: 1 a 10
- t en segundos
- máximo 10 movimientos
- movimientos simultáneos pueden compartir mismo t
Texto: {texto}
"""
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": prompt}]
        )
        contenido = response.choices[0].message.content
        return json.loads(contenido)
    except json.JSONDecodeError as e:
        print("Error al parsear JSON de IA:", e)
        return []
    except Exception as e:
        print("Error llamando a OpenAI:", e)
        return []

# ================= SERIAL =================
class SerialThread(QThread):
    estado_conexion = pyqtSignal(bool)  # True = conectado, False = desconectado

    def __init__(self):
        super().__init__()
        self.arduino = None
        self.queue = deque()
        self.running = True
        self._conectar()

    def _conectar(self):
        try:
            self.arduino = serial.Serial(PORT, BAUD, timeout=0)
            print("Arduino conectado")
            self.estado_conexion.emit(True)
        except Exception as e:
            self.arduino = None
            print(f"Arduino NO conectado: {e}")
            self.estado_conexion.emit(False)

    def run(self):
        while self.running:
            if self.queue and self.arduino:
                cmd = self.queue.popleft()
                try:
                    self.arduino.write(cmd.encode())
                except Exception as e:
                    print(f"Error enviando comando: {e}")
            time.sleep(0.002)

    def enviar(self, cmd):
        self.queue.append(cmd)

    def reconectar(self):
        if self.arduino:
            try:
                self.arduino.close()
            except:
                pass
        self._conectar()

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

# ================= BLOQUE =================
class Bloque(QGraphicsRectItem):
    def __init__(self, pca=0, servo=0, inicio=0, dur=2, pos=500, vel=5, nombre="Servo"):
        super().__init__(0, 0, dur * 120, 40)

        self.pca = pca
        self.servo = servo
        self.inicio = inicio
        self.dur = dur
        self.pos_val = pos
        self.vel = vel
        self.nombre = nombre

        self.text = QGraphicsTextItem(self)
        self.actualizar()

        self.setBrush(QColor(160, 180, 255))
        self.setPen(QPen(QColor(100, 100, 150), 1))

        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setPos(self.inicio * 120, 20)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawRoundedRect(self.rect(), 12, 12)

    def actualizar(self):
        self.text.setPlainText(
            f"{self.nombre}\nP{self.pca} S{self.servo}\nPos:{self.pos_val} V:{self.vel}"
        )
        self.text.setDefaultTextColor(Qt.black)
        self.text.setPos(5, 5)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.inicio = self.pos().x() / 120

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)

        d = QDialog()
        d.setWindowTitle("Editar Servo")

        layout = QFormLayout()

        nombre = QLineEdit(self.nombre)

        pca = QSpinBox()
        pca.setRange(0, 10)
        pca.setValue(self.pca)

        servo = QSpinBox()
        servo.setRange(0, 15)
        servo.setValue(self.servo)

        pos = QSpinBox()
        pos.setRange(0, 1000)
        pos.setValue(self.pos_val)

        vel = QSpinBox()
        vel.setRange(1, 10)
        vel.setValue(self.vel)

        layout.addRow("Nombre", nombre)
        layout.addRow("PCA", pca)
        layout.addRow("Servo", servo)
        layout.addRow("Posición", pos)
        layout.addRow("Velocidad", vel)

        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(d.accept)

        layout.addWidget(btn_ok)
        d.setLayout(layout)

        if d.exec_():
            self.nombre = nombre.text()
            self.pca = pca.value()
            self.servo = servo.value()
            self.pos_val = pos.value()
            self.vel = vel.value()
            self.actualizar()

# ================= ENGINE =================
class Engine(QThread):
    finalizado = pyqtSignal()  # notifica cuando la secuencia termina

    def __init__(self, bloques, serial, estado):
        super().__init__()
        self.bloques = bloques
        self.serial = serial
        self.running = True
        self.estado = estado

    def run(self):
        t0 = time.time()
        ejecutados = set()

        while self.running:
            t = time.time() - t0

            for i, b in enumerate(self.bloques):
                if i in ejecutados:
                    continue
                if t >= b.inicio:
                    cmd = f"PCA,{b.pca},{b.servo},{b.pos_val},{b.vel}\n"
                    self.serial.enviar(cmd)
                    self.estado[(b.pca, b.servo)] = b.pos_val
                    ejecutados.add(i)

            if len(ejecutados) == len(self.bloques):
                break

            time.sleep(0.01)

        self.finalizado.emit()

    def stop(self):
        self.running = False

# ================= UI =================
class UI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("R-ONE Motion Studio v1.0")
        self.setGeometry(100, 100, 1600, 900)

        self.serial = SerialThread()
        self.serial.start()

        self.scene = QGraphicsScene(0, 0, 4000, 1100)
        self.view = QGraphicsView(self.scene)

        self.view.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.view.horizontalScrollBar().setValue(0)
        self.view.verticalScrollBar().setValue(0)
        self.view.setRenderHint(QPainter.Antialiasing)

        self.view.setStyleSheet("""
            QGraphicsView {
                background-color: #f4f6ff;
                border: 2px solid #9aaeff;
                border-radius: 10px;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background: transparent;
                margin: 0px;
                width: 8px;
                height: 8px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #a0b8ff;
                border-radius: 4px;
                min-height: 20px;
                min-width: 20px;
            }
            QScrollBar::handle:hover { background: #7f9cff; }
            QScrollBar::add-line, QScrollBar::sub-line {
                height: 0px; width: 0px;
                background: none; border: none;
            }
            QScrollBar::add-page, QScrollBar::sub-page { background: none; }
            QScrollBar::corner { background: transparent; }
        """)

        self.bloques = []
        self.engine = None
        self.engine_corriendo = False  # guard: evita engines simultáneos
        self.servos_usados = set()

        self.estado_actual = {}
        self.estado_anterior = {}

        self.dibujar_regla()

        # ===== BOTONES =====
        btn_add     = QPushButton("➕ Agregar")
        btn_play    = QPushButton("▶ Play")
        btn_stop    = QPushButton("🛑 Stop")
        btn_center  = QPushButton("🎯 Centrar")
        btn_back    = QPushButton("↩ Volver")
        btn_save    = QPushButton("💾 Guardar")
        btn_load    = QPushButton("📂 Cargar")
        btn_refresh = QPushButton("🔄 Refrescar")

        estilo_boton(btn_add,     "#b8c6ff")
        estilo_boton(btn_play,    "#a0b8ff")
        estilo_boton(btn_stop,    "#ffb3b3")
        estilo_boton(btn_center,  "#d6b3ff")
        estilo_boton(btn_back,    "#ffd6b3")
        estilo_boton(btn_save,    "#b3ffe0")
        estilo_boton(btn_load,    "#cce0ff")
        estilo_boton(btn_refresh, "#e0e0e0")

        btn_add.clicked.connect(self.add)
        btn_play.clicked.connect(self.play)
        btn_stop.clicked.connect(self.stop)
        btn_center.clicked.connect(self.center_all)
        btn_back.clicked.connect(self.back)
        btn_save.clicked.connect(self.save)
        btn_load.clicked.connect(self.load_selected)
        btn_refresh.clicked.connect(self.cargar_lista)

        # ===== IA =====
        self.input_ia = QLineEdit()
        self.input_ia.setPlaceholderText("Describe un movimiento...")
        self.input_ia.setStyleSheet("""
            QLineEdit {
                border: 2px solid #a0b8ff;
                border-radius: 8px;
                padding: 6px;
                background: white;
                font-size: 12px;
            }
        """)
        btn_ia = QPushButton("🧠 Generar IA")
        estilo_boton(btn_ia, "#e0d0ff")
        btn_ia.clicked.connect(self.usar_ia)

        # ===== INDICADOR ARDUINO =====
        self.lbl_conexion = QLabel("⚪ Verificando...")
        self.lbl_conexion.setAlignment(Qt.AlignCenter)
        self.lbl_conexion.setStyleSheet("font-weight: bold; font-size: 11px;")
        self.serial.estado_conexion.connect(self.actualizar_indicador)
        self.actualizar_indicador(self.serial.arduino is not None)

        btn_reconectar = QPushButton("🔌 Reconectar")
        estilo_boton(btn_reconectar, "#ffe0b3")
        btn_reconectar.clicked.connect(self.reconectar_serial)

        # ===== LISTA =====
        self.lista = QListWidget()
        self.cargar_lista()

        # ===== LAYOUT IZQUIERDO =====
        def separador():
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("color: #c0c8ff;")
            return line

        left = QVBoxLayout()
        left.setSpacing(6)

        left.addWidget(QLabel("── Secuencia ──"))
        for b in [btn_add, btn_play, btn_stop, btn_center, btn_back]:
            left.addWidget(b)

        left.addWidget(separador())
        left.addWidget(QLabel("── Archivos ──"))
        for b in [btn_save, btn_load, btn_refresh]:
            left.addWidget(b)

        left.addWidget(separador())
        left.addWidget(QLabel("── IA ──"))
        left.addWidget(self.input_ia)
        left.addWidget(btn_ia)

        left.addWidget(separador())
        left.addWidget(QLabel("── Arduino ──"))
        left.addWidget(self.lbl_conexion)
        left.addWidget(btn_reconectar)

        left.addStretch()

        # ===== LAYOUT DERECHO =====
        right = QVBoxLayout()
        right.addWidget(QLabel("SECUENCIAS GUARDADAS"))
        right.addWidget(self.lista)

        # ===== LAYOUT PRINCIPAL =====
        main = QHBoxLayout()
        main.addLayout(left)
        main.addWidget(self.view, 3)
        main.addLayout(right, 1)

        c = QWidget()
        c.setLayout(main)
        self.setCentralWidget(c)

    # ===== INDICADOR ARDUINO =====
    def actualizar_indicador(self, conectado):
        if conectado:
            self.lbl_conexion.setText("🟢 Arduino conectado")
            self.lbl_conexion.setStyleSheet("font-weight: bold; font-size: 11px; color: green;")
        else:
            self.lbl_conexion.setText("🔴 Sin conexión")
            self.lbl_conexion.setStyleSheet("font-weight: bold; font-size: 11px; color: red;")

    def reconectar_serial(self):
        self.serial.reconectar()

    # ===== REGLA =====
    def dibujar_regla(self):
        for i in range(31):
            x = i * 120
            self.scene.addLine(x, 20, x, 1100, QPen(QColor(180, 180, 200)))
            text = self.scene.addText(f"{i}s")
            text.setDefaultTextColor(Qt.black)
            text.setPos(x, 0)

    def siguiente_servo(self):
        for pca in range(3):
            for s in range(16):
                if (pca, s) not in self.servos_usados:
                    self.servos_usados.add((pca, s))
                    return pca, s
        return 0, 0

    def add(self):
        pca, servo = self.siguiente_servo()
        b = Bloque(pca=pca, servo=servo, nombre=f"P{pca}_S{servo}")
        self.scene.addItem(b)
        self.bloques.append(b)
        self.reorganizar()

    def reorganizar(self):
        self.bloques.sort(key=lambda b: (b.pca, b.servo))
        for i, b in enumerate(self.bloques):
            b.setPos(b.inicio * 120, i * 50 + 20)

    # ===== PLAY con guard =====
    def play(self):
        if self.engine_corriendo:
            QMessageBox.warning(
                self, "En ejecución",
                "Ya hay una secuencia en curso.\nPresiona 🛑 Stop antes de volver a ejecutar."
            )
            return

        if not self.bloques:
            QMessageBox.information(self, "Sin bloques", "Agrega al menos un bloque antes de ejecutar.")
            return

        self.estado_anterior = self.estado_actual.copy()
        self.engine = Engine(self.bloques, self.serial, self.estado_actual)
        self.engine.finalizado.connect(self._engine_finalizado)
        self.engine_corriendo = True
        self.engine.start()

    def _engine_finalizado(self):
        self.engine_corriendo = False

    def stop(self):
        if self.engine:
            self.engine.stop()
        self.engine_corriendo = False

    # ===== CENTRAR =====
    def center_all(self):
        self.estado_anterior = self.estado_actual.copy()
        for b in self.bloques:
            cmd = f"PCA,{b.pca},{b.servo},500,5\n"
            self.serial.enviar(cmd)
            self.estado_actual[(b.pca, b.servo)] = 500

    # ===== VOLVER =====
    def back(self):
        for (pca, servo), pos in self.estado_anterior.items():
            cmd = f"PCA,{pca},{servo},{pos},5\n"
            self.serial.enviar(cmd)
            self.estado_actual[(pca, servo)] = pos

    # ===== GUARDAR =====
    def save(self):
        nombre, ok = QInputDialog.getText(self, "Guardar", "Nombre del archivo:")
        if ok and nombre:
            path = os.path.join(BASE_PATH, nombre + ".json")

            if os.path.exists(path):
                resp = QMessageBox.question(
                    self, "Sobreescribir",
                    f"'{nombre}.json' ya existe. ¿Sobreescribir?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if resp != QMessageBox.Yes:
                    return

            data = []
            for b in self.bloques:
                data.append([b.pca, b.servo, b.inicio, b.dur, b.pos_val, b.vel, b.nombre])

            with open(path, "w") as f:
                json.dump(data, f)

            self.cargar_lista()

    # ===== LISTA =====
    def cargar_lista(self):
        self.lista.clear()
        for f in sorted(os.listdir(BASE_PATH)):
            if f.endswith(".json"):
                self.lista.addItem(f)

    # ===== CARGAR con confirmación =====
    def load_selected(self):
        item = self.lista.currentItem()
        if not item:
            return

        if self.bloques:
            resp = QMessageBox.question(
                self, "Cargar secuencia",
                "¿Cargar esta secuencia? Los bloques actuales sin guardar se perderán.",
                QMessageBox.Yes | QMessageBox.No
            )
            if resp != QMessageBox.Yes:
                return

        path = os.path.join(BASE_PATH, item.text())

        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer el archivo:\n{e}")
            return

        self.scene.clear()
        self.bloques.clear()
        self.servos_usados.clear()
        self.estado_actual.clear()

        for d in data:
            b = Bloque(*d)
            self.scene.addItem(b)
            self.bloques.append(b)
            self.servos_usados.add((b.pca, b.servo))
            self.estado_actual[(b.pca, b.servo)] = b.pos_val

        self.dibujar_regla()
        self.reorganizar()

    # ===== IA =====
    def usar_ia(self):
        texto = self.input_ia.text().strip()
        if not texto:
            return

        movimientos = generar_movimiento_ia(texto)

        if not movimientos:
            QMessageBox.warning(
                self, "IA",
                "No se pudieron generar movimientos.\nRevisa la API key o la conexión a OpenAI."
            )
            return

        for m in movimientos:
            QTimer.singleShot(
                int(m["t"] * 1000),
                lambda m=m: self.serial.enviar(
                    f'PCA,{m["pca"]},{m["servo"]},{m["pos"]},{m["vel"]}\n'
                )
            )

        resumen = "\n".join(
            f"t={m['t']}s → PCA{m['pca']} S{m['servo']}  pos={m['pos']}  vel={m['vel']}"
            for m in movimientos
        )
        QMessageBox.information(self, "IA — Movimientos generados", resumen)

    def closeEvent(self, e):
        self.serial.stop()
        if self.engine:
            self.engine.stop()
        e.accept()

# ================= RUN =================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    aplicar_tema(app)
    w = UI()
    w.show()
    sys.exit(app.exec_())
