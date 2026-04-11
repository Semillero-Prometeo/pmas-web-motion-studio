import sys
import time
import os
import json
import serial
import serial.tools.list_ports
from collections import deque

from openai import OpenAI

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

BAUD = 115200

# Palabras clave para identificar un Arduino en la lista de puertos
ARDUINO_KEYWORDS = ["arduino", "ch340", "ch341", "cp210", "ftdi", "usb serial", "usb-serial"]

def detectar_puerto_arduino():
    """
    Busca automáticamente un puerto que corresponda a un Arduino.
    Retorna el nombre del puerto (ej. 'COM3', '/dev/ttyUSB0') o None si no encuentra.
    """
    puertos = list(serial.tools.list_ports.comports())
    for p in puertos:
        descripcion = (p.description or "").lower()
        fabricante  = (p.manufacturer or "").lower()
        if any(k in descripcion or k in fabricante for k in ARDUINO_KEYWORDS):
            print(f"Arduino detectado automáticamente: {p.device} — {p.description}")
            return p.device
    # Si hay un solo puerto disponible, usarlo directamente
    if len(puertos) == 1:
        print(f"Un solo puerto disponible, usando: {puertos[0].device}")
        return puertos[0].device
    return None

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
    estado_conexion  = pyqtSignal(bool)
    pcas_detectadas  = pyqtSignal(list)   # emite lista de ints, ej. [0, 1, 3]

    def __init__(self):
        super().__init__()
        self.arduino = None
        self.puerto_actual = None
        self.queue = deque()
        self.running = True
        self._buf = ""
        self._conectar()

    def _conectar(self):
        puerto = detectar_puerto_arduino()
        if not puerto:
            self.arduino = None
            self.puerto_actual = None
            print("Arduino NO encontrado: no se detectó ningún puerto compatible.")
            self.estado_conexion.emit(False)
            return
        try:
            self.arduino = serial.Serial(puerto, BAUD, timeout=0)
            self.puerto_actual = puerto
            print(f"Arduino conectado en {puerto}")
            self.estado_conexion.emit(True)
            # Pedir escaneo de PCAs al arrancar (tras reset del Arduino)
            QTimer.singleShot(2000, lambda: self.queue.append("SCAN\n"))
        except Exception as e:
            self.arduino = None
            self.puerto_actual = None
            print(f"Arduino NO conectado ({puerto}): {e}")
            self.estado_conexion.emit(False)

    def run(self):
        while self.running:
            if self.queue and self.arduino and self.arduino.is_open:
                cmd = self.queue.popleft()
                try:
                    self.arduino.write(cmd.encode())
                except Exception as e:
                    print(f"Error enviando comando: {e}")
            elif self.queue and not self.arduino:
                self.queue.popleft()
            # Leer respuestas del Arduino
            if self.arduino and self.arduino.is_open:
                try:
                    n = self.arduino.in_waiting
                    if n > 0:
                        self._buf += self.arduino.read(n).decode(errors='ignore')
                        while '\n' in self._buf:
                            linea, self._buf = self._buf.split('\n', 1)
                            self._procesar_respuesta(linea.strip())
                except Exception:
                    pass
            time.sleep(0.002)

    def _procesar_respuesta(self, linea):
        if linea.startswith("PCAS:"):
            parte = linea[5:]
            pcas = [int(x) for x in parte.split(",") if x.strip().isdigit()] if parte else []
            print(f"PCAs detectadas: {pcas}")
            self.pcas_detectadas.emit(pcas)

    def enviar(self, cmd):
        self.queue.append(cmd)

    def escanear_pcas(self):
        self.queue.append("SCAN\n")

    def reconectar(self):
        if self.arduino:
            try:
                self.arduino.close()
            except:
                pass
        self._buf = ""
        self._conectar()

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

# ================= BLOQUE =================
BLOCK_H = 30          # altura reducida del bloque
BLOCK_PX = 100        # píxeles por segundo (era 120)
BLOCK_ROW_H = 40      # separación entre filas (era 50)

R_BTN = 7  # radio del botón eliminar

class BotonEliminar(QGraphicsEllipseItem):
    """Botón rojo redondo — centro exactamente en setPos(), sobresale del bloque."""
    def __init__(self, parent_bloque):
        # rect centrado en (0,0): (-R, -R, 2R, 2R)
        super().__init__(-R_BTN, -R_BTN, R_BTN * 2, R_BTN * 2, parent_bloque)
        self.parent_bloque = parent_bloque
        self.setBrush(QColor(220, 50, 50))
        self.setPen(QPen(QColor(160, 20, 20), 1))
        self.setZValue(10)
        self.setCursor(Qt.PointingHandCursor)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawEllipse(self.rect())
        # Cruz blanca centrada en (0,0)
        painter.setPen(QPen(Qt.white, 1.8, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(QPointF(-3.5, -3.5), QPointF(3.5, 3.5))
        painter.drawLine(QPointF(3.5, -3.5), QPointF(-3.5, 3.5))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            scene = self.parent_bloque.scene()
            if scene and hasattr(scene, 'parent_ui'):
                scene.parent_ui.eliminar_bloque(self.parent_bloque)

# Paleta de 5 colores base (normal) y su versión oscura (solapado)
COLORES_FILA = [
    (QColor(160, 180, 255), QColor(100, 120, 210)),   # azul
    (QColor(160, 220, 180), QColor( 80, 160, 100)),   # verde
    (QColor(255, 200, 130), QColor(210, 140,  50)),   # naranja
    (QColor(220, 160, 255), QColor(160,  90, 210)),   # violeta
    (QColor(255, 160, 160), QColor(210,  80,  80)),   # rojo
]

def color_para_fila(fila, solapado=False):
    base, oscuro = COLORES_FILA[fila % len(COLORES_FILA)]
    return base if solapado else oscuro


class Bloque(QGraphicsRectItem):
    def __init__(self, pca=0, servo=0, inicio=0, dur=2, pos=500, vel=5, nombre="Servo"):
        super().__init__(0, 0, dur * BLOCK_PX, BLOCK_H)

        self.pca = pca
        self.servo = servo
        self.inicio = inicio
        self.dur = dur
        self.pos_val = pos
        self.vel = vel
        self.nombre = nombre
        self.fila = 0          # asignada por reorganizar()

        self.text = QGraphicsTextItem(self)
        self.actualizar()

        self.setBrush(color_para_fila(0))
        self.setPen(QPen(QColor(80, 80, 120), 1))

        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setPos(self.inicio * BLOCK_PX, 20)

        # Botón eliminar: centro en la esquina superior derecha
        self.btn_x = BotonEliminar(self)
        self.btn_x.setPos(dur * BLOCK_PX, 0)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawRoundedRect(self.rect(), 8, 8)

    def actualizar(self):
        self.text.setPlainText(
            f"{self.nombre}  P{self.pca}S{self.servo}  Pos:{self.pos_val} V:{self.vel}"
        )
        self.text.setDefaultTextColor(Qt.white)
        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        self.text.setFont(font)
        self.text.setPos(5, 6)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # Movimiento horizontal libre — solo actualizar inicio (sin snap)
        self.inicio = max(0.0, self.pos().x() / BLOCK_PX)

        # Detectar fila destino por posición Y arrastrada e intercambiar servos
        scene = self.scene()
        if scene and hasattr(scene, 'parent_ui'):
            ui = scene.parent_ui
            y_actual = self.pos().y()
            fila_destino = round((y_actual - 20) / BLOCK_ROW_H)
            fila_destino = max(0, fila_destino)

            # Obtener un representante por fila (el primer bloque de cada fila real)
            # usando b.fila que reorganizar() ya asignó correctamente,
            # ignorando bloques que comparten fila con 'self' (superposición)
            filas_vistas = {}
            for b in ui.bloques:
                if b is not self and b.fila not in filas_vistas:
                    filas_vistas[b.fila] = b

            if fila_destino in filas_vistas:
                bloque_destino = filas_vistas[fila_destino]
                self.pca,   bloque_destino.pca   = bloque_destino.pca,   self.pca
                self.servo, bloque_destino.servo  = bloque_destino.servo, self.servo
                self.nombre  = f"P{self.pca}_S{self.servo}"
                bloque_destino.nombre = f"P{bloque_destino.pca}_S{bloque_destino.servo}"
                self.actualizar()
                bloque_destino.actualizar()

            ui.reorganizar()

    def mouseDoubleClickEvent(self, event):
        # Ignorar doble clic sobre el botón eliminar
        local = self.mapFromScene(event.scenePos())
        btn_pos = self.btn_x.pos()
        if (local - btn_pos).manhattanLength() < 12:
            return

        super().mouseDoubleClickEvent(event)

        d = QDialog()
        d.setWindowTitle("Editar Servo")
        layout = QFormLayout()

        nombre = QLineEdit(self.nombre)
        pca   = QSpinBox(); pca.setRange(0, 10);   pca.setValue(self.pca)
        servo = QSpinBox(); servo.setRange(0, 15);  servo.setValue(self.servo)
        pos   = QSpinBox(); pos.setRange(0, 1000);  pos.setValue(self.pos_val)
        vel   = QSpinBox(); vel.setRange(1, 10);    vel.setValue(self.vel)

        layout.addRow("Nombre",    nombre)
        layout.addRow("PCA",       pca)
        layout.addRow("Servo",     servo)
        layout.addRow("Posición",  pos)
        layout.addRow("Velocidad", vel)

        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(d.accept)
        layout.addWidget(btn_ok)
        d.setLayout(layout)

        if d.exec_():
            self.nombre   = nombre.text()
            self.pca      = pca.value()
            self.servo    = servo.value()
            self.pos_val  = pos.value()
            self.vel      = vel.value()
            self.actualizar()
            # Notificar a la UI para que reordene y colapse filas vacías
            scene = self.scene()
            if scene and hasattr(scene, 'parent_ui'):
                scene.parent_ui.reorganizar()

# ================= PLAYHEAD =================
class Playhead(QGraphicsLineItem):
    def __init__(self, height=1100):
        super().__init__(0, 0, 0, height)
        self.setPen(QPen(QColor(255, 80, 80), 2, Qt.SolidLine))
        self.setZValue(100)
        # Triángulo indicador en la parte superior
        self.triangle = QGraphicsPolygonItem(self)
        poly = QPolygonF([
            QPointF(-6, -14),
            QPointF(6, -14),
            QPointF(0, 0),
        ])
        self.triangle.setPolygon(poly)
        self.triangle.setBrush(QColor(255, 80, 80))
        self.triangle.setPen(QPen(Qt.NoPen))

    def set_time(self, t_seconds):
        x = t_seconds * BLOCK_PX
        self.setX(x)

# ================= ENGINE =================
class Engine(QThread):
    finalizado = pyqtSignal()
    tick = pyqtSignal(float)   # emite el tiempo actual en segundos

    def __init__(self, bloques_snapshot, serial, estado):
        super().__init__()
        # ✅ FIX: recibir snapshot inmutable de los datos de bloques,
        #        no referencias a los objetos QGraphics (pueden eliminarse mid-run)
        self.bloques = bloques_snapshot
        self.serial = serial
        self.running = True
        self.estado = estado

    def run(self):
        t0 = time.time()
        ejecutados = set()
        n = len(self.bloques)

        while self.running:
            t = time.time() - t0
            self.tick.emit(t)

            for i, b in enumerate(self.bloques):
                if i in ejecutados:
                    continue
                if t >= b['inicio']:
                    cmd = f"PCA,{b['pca']},{b['servo']},{b['pos_val']},{b['vel']}\n"
                    self.serial.enviar(cmd)
                    self.estado[(b['pca'], b['servo'])] = b['pos_val']
                    ejecutados.add(i)

            if len(ejecutados) == n:
                break

            time.sleep(0.01)

        self.tick.emit(0.0)
        self.finalizado.emit()

    def stop(self):
        self.running = False

# ================= SCENE con referencia a UI =================
class Scene(QGraphicsScene):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_ui = None  # se asigna desde UI.__init__

# ================= UI =================
class UI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("R-ONE Motion Studio v1.0")
        self.setGeometry(0, 0, 1600, 900)   # ← esquina superior izquierda

        self.serial = SerialThread()
        self.serial.start()

        # Usar Scene personalizada para que los bloques puedan notificar eliminación
        self.scene = Scene(0, 0, 4000, 1100)
        self.scene.parent_ui = self

        self.view = QGraphicsView(self.scene)
        self.view.setAlignment(Qt.AlignLeft | Qt.AlignTop)
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
        self.engine_corriendo = False
        self.servos_usados = set()

        self.estado_actual = {}
        self.estado_anterior = {}

        # Playhead
        self.playhead = Playhead(height=1100)
        self.playhead.setVisible(False)
        self.scene.addItem(self.playhead)

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

        self.lbl_pcas = QLabel("PCAs: —")
        self.lbl_pcas.setAlignment(Qt.AlignCenter)
        self.lbl_pcas.setStyleSheet("font-size: 11px; color: #555;")
        self.serial.pcas_detectadas.connect(self.actualizar_pcas)

        btn_reconectar = QPushButton("🔌 Reconectar")
        estilo_boton(btn_reconectar, "#ffe0b3")
        btn_reconectar.clicked.connect(self.reconectar_serial)

        btn_scan = QPushButton("🔍 Escanear PCAs")
        estilo_boton(btn_scan, "#d0f0d0")
        btn_scan.clicked.connect(self.serial.escanear_pcas)

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
        left.addWidget(self.lbl_pcas)
        left.addWidget(btn_reconectar)
        left.addWidget(btn_scan)

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
            puerto = getattr(self.serial, 'puerto_actual', '') or ''
            self.lbl_conexion.setText(f"🟢 Arduino conectado\n{puerto}")
            self.lbl_conexion.setStyleSheet("font-weight: bold; font-size: 11px; color: green;")
        else:
            self.lbl_conexion.setText("🔴 Sin conexión")
            self.lbl_conexion.setStyleSheet("font-weight: bold; font-size: 11px; color: red;")

    def actualizar_pcas(self, pcas):
        if pcas:
            texto = "  ".join(f"PCA{i} 🟢" for i in pcas)
        else:
            texto = "Sin PCAs detectadas"
        self.lbl_pcas.setText(texto)
        self.lbl_pcas.setStyleSheet("font-size: 11px; color: #333; font-weight: bold;")

    def reconectar_serial(self):
        self.serial.reconectar()

    # ===== REGLA =====
    def dibujar_regla(self):
        for i in range(41):
            x = i * BLOCK_PX
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

    def eliminar_bloque(self, bloque):
        """Elimina un bloque de la escena y de la lista."""
        if bloque in self.bloques:
            self.bloques.remove(bloque)
            self.scene.removeItem(bloque)
            # Solo liberar el servo si no quedan más bloques con ese (pca, servo)
            aun_usado = any(b.pca == bloque.pca and b.servo == bloque.servo for b in self.bloques)
            if not aun_usado:
                self.servos_usados.discard((bloque.pca, bloque.servo))
            self.reorganizar()

    def reorganizar(self):
        from collections import defaultdict
        grupos = defaultdict(list)
        for b in self.bloques:
            grupos[(b.pca, b.servo)].append(b)

        filas_ordenadas = sorted(grupos.keys())

        for fila_idx, clave in enumerate(filas_ordenadas):
            # Ordenar bloques de esta fila por inicio para numerar su color
            bloques_fila = sorted(grupos[clave], key=lambda b: b.inicio)

            for orden, b in enumerate(bloques_fila):
                b.fila = fila_idx
                b.setPos(b.inicio * BLOCK_PX, fila_idx * BLOCK_ROW_H + 20)

                # Color: índice = posición del bloque en su fila (0=azul, 1=verde…)
                solapado = any(
                    otro is not b
                    and b.inicio < (otro.inicio + otro.dur)
                    and (b.inicio + b.dur) > otro.inicio
                    for otro in bloques_fila
                )
                b.setBrush(color_para_fila(orden, solapado))
                b.setPen(QPen(QColor(60, 60, 100), 1.5 if solapado else 1))

    # ===== PLAY =====
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

        # ✅ FIX PRINCIPAL: snapshot de datos puros (dict), no referencias a objetos QGraphics
        snapshot = [
            {
                'pca': b.pca,
                'servo': b.servo,
                'inicio': b.inicio,
                'pos_val': b.pos_val,
                'vel': b.vel,
            }
            for b in self.bloques
        ]

        self.engine = Engine(snapshot, self.serial, self.estado_actual)
        self.engine.finalizado.connect(self._engine_finalizado)
        self.engine.tick.connect(self._actualizar_playhead)
        self.engine_corriendo = True

        self.playhead.set_time(0)
        self.playhead.setVisible(True)

        self.engine.start()

    def _engine_finalizado(self):
        self.engine_corriendo = False
        self.playhead.setVisible(False)

    def _actualizar_playhead(self, t):
        self.playhead.set_time(t)
        # Auto-scroll para seguir el playhead
        x_scene = t * BLOCK_PX
        self.view.ensureVisible(QRectF(x_scene - 50, 0, 200, 100), 50, 0)

    def stop(self):
        if self.engine:
            self.engine.stop()
        self.engine_corriendo = False
        self.playhead.setVisible(False)

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

    # ===== CARGAR =====
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

        # Re-crear playhead tras scene.clear()
        self.playhead = Playhead(height=1100)
        self.playhead.setVisible(False)
        self.scene.addItem(self.playhead)

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

    def showEvent(self, event):
        super().showEvent(event)
        # Forzar scroll a esquina superior izquierda después de que el widget se pinte
        QTimer.singleShot(0, lambda: (
            self.view.horizontalScrollBar().setValue(0),
            self.view.verticalScrollBar().setValue(0)
        ))

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
