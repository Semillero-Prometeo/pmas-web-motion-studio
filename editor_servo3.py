import sys
import os
import json

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# ─── RUTAS ────────────────────────────────────────────────────────────────────
USER_HOME  = os.path.expanduser("~")
BASE_PATH  = os.path.join(USER_HOME, "Desktop", "R-One")
SERVO_FILE = os.path.join(BASE_PATH, "servos.json")
os.makedirs(BASE_PATH, exist_ok=True)

# ─── DATOS ────────────────────────────────────────────────────────────────────
SERVO_MODELOS = {
    "DS5160":    "4.8 – 8.4 V",
    "MG996R":    "4.8 – 7.2 V",
    "PDI6221MG": "4.8 – 6.6 V",
    "SG90":      "4.8 – 6.0 V",
    "Otro":      "Definir",
}

UBICACIONES = [
    "Brazo derecho",
    "Brazo izquierdo",
    "Bíceps derecho",
    "Bíceps izquierdo",
    "Cabeza",
    "Cadera",
    "Cuello",
    "Torso",
]

MOVIMIENTOS = sorted([
    "antihorario", "baja", "contrae", "derecha",
    "hacia adentro", "hacia afuera", "horario",
    "izquierda", "libera", "sube",
])

# ─── TEMA ─────────────────────────────────────────────────────────────────────
def aplicar_tema(app):
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window,          QColor(235, 240, 255))
    p.setColor(QPalette.WindowText,      Qt.black)
    p.setColor(QPalette.Base,            QColor(255, 255, 255))
    p.setColor(QPalette.Text,            Qt.black)
    p.setColor(QPalette.Button,          QColor(210, 220, 255))
    p.setColor(QPalette.ButtonText,      Qt.black)
    p.setColor(QPalette.Highlight,       QColor(140, 170, 255))
    p.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(p)

def estilo_boton(btn, color):
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {color};
            border-radius: 10px;
            padding: 8px 14px;
            color: black;
            font-weight: bold;
            font-size: 12px;
        }}
        QPushButton:hover {{ background-color: #d0d8ff; }}
        QPushButton:pressed {{ background-color: #a0b0ee; }}
    """)
    btn.setFixedHeight(38)

FIELD_STYLE = """
    QLineEdit, QComboBox, QSpinBox {
        border: 2px solid #a0b8ff;
        border-radius: 7px;
        padding: 4px 8px;
        background: white;
        font-size: 12px;
        min-height: 26px;
    }
    QComboBox {
        padding-right: 20px;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: right center;
        width: 20px;
        border: none;
        background: transparent;
    }
    QComboBox::down-arrow {
        image: none;
        width: 0px;
        height: 0px;
        border-left:   5px solid transparent;
        border-right:  5px solid transparent;
        border-top:    6px solid #6080cc;
        margin-right:  6px;
    }
    QComboBox QAbstractItemView {
        border: 2px solid #a0b8ff;
        border-radius: 7px;
        background: white;
        selection-background-color: #c8d8ff;
        selection-color: #1a2a6a;
        color: #1a2a5a;
        padding: 2px;
        outline: none;
    }
    QComboBox QAbstractItemView::item {
        min-height: 24px;
        padding: 3px 8px;
        border-radius: 4px;
    }
    QComboBox QAbstractItemView::item:hover {
        background: #e8eeff;
        color: #1a2a6a;
    }
    QComboBox QAbstractItemView::item:selected {
        background: #c8d8ff;
        color: #1a2a6a;
    }
    QSpinBox::up-button, QSpinBox::down-button { width: 0px; border: none; }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
        border-color: #6080ff;
    }
    QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {
        background: #e8eaff; color: #7080a0;
    }
"""

ERROR_STYLE = "font-size: 11px; color: #cc2200; font-weight: bold;"

LABEL_STYLE  = "font-size: 12px; font-weight: bold; color: #3a4a8a;"
VALUE_STYLE  = """
    background: #eef0ff;
    border: 2px solid #c0caff;
    border-radius: 7px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: bold;
    color: #2a3a7a;
    min-height: 26px;
"""

# ─── PERSISTENCIA ─────────────────────────────────────────────────────────────
def cargar_datos():
    if os.path.exists(SERVO_FILE):
        try:
            with open(SERVO_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Claves como int
            return {int(k): {int(c): v for c, v in ch.items()} for k, ch in raw.items()}
        except Exception:
            pass
    return {}

def guardar_datos(data):
    with open(SERVO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ─── NOMBRE CORTO ubicacion+tipo ──────────────────────────────────────────────
_ABREV_UBIC = {
    "brazo derecho":    "bra_der",
    "brazo izquierdo":  "bra_izq",
    "bíceps derecho":   "bic_der",
    "bíceps izquierdo": "bic_izq",
    "cabeza":           "cab",
    "cadera":           "cad",
    "cuello":           "cue",
    "torso":            "tor",
}

def generar_nombre_corto(ubicacion, tipo_mov):
    """Genera un slug corto tipo bra_izq_flexion."""
    ubic_key = ubicacion.lower().strip()
    abrev    = _ABREV_UBIC.get(ubic_key, ubic_key.replace(" ", "_")[:7])
    # Normalizar tipo: minúsculas, sin tildes básicas, espacios→_
    import unicodedata
    tipo_norm = unicodedata.normalize("NFD", tipo_mov.lower().strip())
    tipo_norm = "".join(c for c in tipo_norm
                        if unicodedata.category(c) != "Mn")
    tipo_norm = tipo_norm.replace(" ", "_")
    # Quitar caracteres no alfanuméricos excepto _
    tipo_norm = "".join(c for c in tipo_norm if c.isalnum() or c == "_")
    return f"{abrev}_{tipo_norm}"

# ─── PANEL DE FORMULARIO ──────────────────────────────────────────────────────
class FormPanel(QWidget):
    servo_guardado = pyqtSignal()

    def __init__(self, data):
        super().__init__()
        self.data = data
        self._build()

    def _lbl(self, texto):
        l = QLabel(texto)
        l.setStyleSheet(LABEL_STYLE)
        return l

    def _val_lbl(self):
        l = QLabel("—")
        l.setStyleSheet(VALUE_STYLE)
        l.setAlignment(Qt.AlignCenter)
        return l

    def _build(self):
        self.setStyleSheet(FIELD_STYLE)
        self._modo_edicion = False

        grid = QGridLayout(self)
        grid.setSpacing(10)
        grid.setContentsMargins(18, 18, 18, 18)

        # ── PCA ──
        grid.addWidget(self._lbl("PCA"), 0, 0)
        self.pca_cb = QComboBox()
        self.pca_cb.addItems(["0","1","2","3"])
        self.pca_cb.currentIndexChanged.connect(self._on_pca_canal_change)
        grid.addWidget(self.pca_cb, 0, 1)

        # ── Canal ──
        grid.addWidget(self._lbl("Canal"), 1, 0)
        self.canal_cb = QComboBox()
        self.canal_cb.addItems([str(i) for i in range(16)])
        self.canal_cb.currentIndexChanged.connect(self._on_pca_canal_change)
        grid.addWidget(self.canal_cb, 1, 1)

        # ── Ubicación ──  (ahora debajo de Canal)
        grid.addWidget(self._lbl("Ubicación"), 2, 0)
        self.ubic_cb = QComboBox()
        self.ubic_cb.addItems(UBICACIONES)
        grid.addWidget(self.ubic_cb, 2, 1)

        # ── Tipo de movimiento ──
        grid.addWidget(self._lbl("Tipo de movimiento"), 3, 0)
        self.nombre_le = QLineEdit()
        self.nombre_le.setPlaceholderText("ej. flexion, rotacion, extension…")
        grid.addWidget(self.nombre_le, 3, 1)

        # ── Modelo ──
        grid.addWidget(self._lbl("Modelo"), 4, 0)
        self.modelo_cb = QComboBox()
        self.modelo_cb.addItems(list(SERVO_MODELOS.keys()))
        self.modelo_cb.currentTextChanged.connect(self._on_modelo)
        grid.addWidget(self.modelo_cb, 4, 1)

        # ── Voltaje (display) ──
        grid.addWidget(self._lbl("Voltaje trabajo"), 5, 0)
        self.voltaje_lbl = self._val_lbl()
        grid.addWidget(self.voltaje_lbl, 5, 1)

        # ── Min ticks ──
        grid.addWidget(self._lbl("Mín ticks"), 6, 0)
        self.min_sb = QSpinBox()
        self.min_sb.setRange(0, 1000)
        self.min_sb.setValue(0)
        self.min_sb.valueChanged.connect(self._on_ticks_change)
        grid.addWidget(self.min_sb, 6, 1)

        # ── Max ticks ──
        grid.addWidget(self._lbl("Máx ticks"), 7, 0)
        self.max_sb = QSpinBox()
        self.max_sb.setRange(0, 1000)
        self.max_sb.setValue(1000)
        self.max_sb.valueChanged.connect(self._on_ticks_change)
        grid.addWidget(self.max_sb, 7, 1)

        # ── Error ticks ──
        self.lbl_tick_error = QLabel("")
        self.lbl_tick_error.setStyleSheet(ERROR_STYLE)
        grid.addWidget(self.lbl_tick_error, 8, 0, 1, 2)

        # ── Centro (auto) ──
        grid.addWidget(self._lbl("Centro"), 9, 0)
        self.centro_lbl = self._val_lbl()
        grid.addWidget(self.centro_lbl, 9, 1)

        # ── Movimiento min→max ──
        grid.addWidget(self._lbl("Movimiento de"), 10, 0)
        self.mov_min_cb = QComboBox()
        self.mov_min_cb.addItems(MOVIMIENTOS)
        self.lbl_mov_min = QLabel(f"0 → 1000  =")
        self.lbl_mov_min.setStyleSheet("font-size: 11px; font-weight: bold; color: #3a4a8a; min-width: 90px;")
        self.lbl_mov_min.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row_min = QHBoxLayout()
        row_min.setSpacing(8)
        row_min.addWidget(self.lbl_mov_min)
        row_min.addWidget(self.mov_min_cb, 1)
        grid.addLayout(row_min, 10, 1)

        # ── Movimiento max→min ──
        grid.addWidget(self._lbl(""), 11, 0)
        self.mov_max_cb = QComboBox()
        self.mov_max_cb.addItems(MOVIMIENTOS)
        self.mov_max_cb.setCurrentIndex(1)
        self.lbl_mov_max = QLabel(f"1000 → 0  =")
        self.lbl_mov_max.setStyleSheet("font-size: 11px; font-weight: bold; color: #3a4a8a; min-width: 90px;")
        self.lbl_mov_max.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row_max = QHBoxLayout()
        row_max.setSpacing(8)
        row_max.addWidget(self.lbl_mov_max)
        row_max.addWidget(self.mov_max_cb, 1)
        grid.addLayout(row_max, 11, 1)

        # ── Aviso servo existente ──
        self.lbl_aviso = QLabel("")
        self.lbl_aviso.setStyleSheet("font-size: 11px; color: #b05000; font-weight: bold;")
        self.lbl_aviso.setWordWrap(True)
        grid.addWidget(self.lbl_aviso, 12, 0, 1, 2)

        # ── Botones guardar / editar ──
        btn_row = QHBoxLayout()
        self.btn_guardar = QPushButton("💾  Guardar servo")
        estilo_boton(self.btn_guardar, "#b3ffe0")
        self.btn_guardar.clicked.connect(self._guardar)
        self.btn_editar = QPushButton("✏️  Editar servo")
        estilo_boton(self.btn_editar, "#ffe0b3")
        self.btn_editar.setVisible(False)
        self.btn_editar.clicked.connect(self._activar_edicion)
        btn_row.addWidget(self.btn_guardar)
        btn_row.addWidget(self.btn_editar)
        grid.addLayout(btn_row, 13, 0, 1, 2)

        grid.setColumnStretch(1, 1)

        # init
        self._on_modelo(self.modelo_cb.currentText())
        self._on_ticks_change()
        self._on_pca_canal_change()

    # ── helpers ──
    def _on_modelo(self, modelo):
        self.voltaje_lbl.setText(SERVO_MODELOS.get(modelo, "—"))

    def _on_ticks_change(self):
        mn = self.min_sb.value()
        mx = self.max_sb.value()
        if mn >= mx:
            self.lbl_tick_error.setText(
                f"⚠  Mín ticks ({mn}) debe ser menor que Máx ticks ({mx})")
        else:
            self.lbl_tick_error.setText("")
        self.centro_lbl.setText(str((mn + mx) // 2))
        self.lbl_mov_min.setText(f"{mn} → {mx}  =")
        self.lbl_mov_max.setText(f"{mx} → {mn}  =")

    def _on_pca_canal_change(self):
        if self._modo_edicion:
            return
        pca   = int(self.pca_cb.currentText())
        canal = int(self.canal_cb.currentText())
        existe = canal in self.data.get(pca, {})
        if existe:
            nombre = self.data[pca][canal].get("nombre", "")
            self.lbl_aviso.setText(
                f"⚠  PCA {pca} · Canal {canal} ya tiene '{nombre}' configurado.\n"
                f"Pulsa  ✏️ Editar servo  para modificarlo.")
            self.lbl_aviso.setStyleSheet(
                "font-size: 11px; color: #b05000; font-weight: bold;")
            self._bloquear_campos(True)
            self.btn_guardar.setVisible(False)
            self.btn_editar.setVisible(True)
        else:
            self.lbl_aviso.setText("")
            self._bloquear_campos(False)
            self.btn_guardar.setVisible(True)
            self.btn_editar.setVisible(False)

    def _bloquear_campos(self, bloquear):
        for w in [self.ubic_cb, self.nombre_le, self.modelo_cb,
                  self.min_sb, self.max_sb, self.mov_min_cb, self.mov_max_cb]:
            w.setEnabled(not bloquear)

    def _activar_edicion(self):
        pca   = int(self.pca_cb.currentText())
        canal = int(self.canal_cb.currentText())
        self._modo_edicion = True
        self.cargar_servo(pca, canal)
        self._bloquear_campos(False)
        self.pca_cb.setEnabled(False)
        self.canal_cb.setEnabled(False)
        self.lbl_aviso.setText("✏️  Modo edición — modifica los campos y guarda.")
        self.lbl_aviso.setStyleSheet(
            "font-size: 11px; color: #1a6a20; font-weight: bold;")
        self.btn_guardar.setVisible(True)
        self.btn_editar.setVisible(False)

    def _reset_modo(self):
        self._modo_edicion = False
        self.pca_cb.setEnabled(True)
        self.canal_cb.setEnabled(True)
        self.lbl_aviso.setStyleSheet(
            "font-size: 11px; color: #b05000; font-weight: bold;")
        self._on_pca_canal_change()

    def cargar_servo(self, pca, canal):
        """Rellena el formulario con datos existentes."""
        d = self.data.get(pca, {}).get(canal)
        if not d:
            self.nombre_le.clear()
            self.ubic_cb.setCurrentIndex(0)
            self.modelo_cb.setCurrentIndex(0)
            self.min_sb.setValue(0)
            self.max_sb.setValue(1000)
            self.mov_min_cb.setCurrentIndex(0)
            self.mov_max_cb.setCurrentIndex(1)
            return

        # Bloquear señales PCA/Canal para no disparar _on_pca_canal_change
        self.pca_cb.blockSignals(True)
        self.canal_cb.blockSignals(True)
        self.pca_cb.setCurrentText(str(pca))
        self.canal_cb.setCurrentText(str(canal))
        self.pca_cb.blockSignals(False)
        self.canal_cb.blockSignals(False)

        self.nombre_le.setText(d.get("nombre", ""))

        idx_u = self.ubic_cb.findText(d.get("ubicacion", ""))
        if idx_u >= 0:
            self.ubic_cb.setCurrentIndex(idx_u)

        modelo = d.get("modelo", "DS5160")
        idx_m = self.modelo_cb.findText(modelo)
        if idx_m >= 0:
            self.modelo_cb.setCurrentIndex(idx_m)

        self.min_sb.setValue(d.get("min", 0))
        self.max_sb.setValue(d.get("max", 1000))

        idx_min = self.mov_min_cb.findText(d.get("mov_min", ""))
        idx_max = self.mov_max_cb.findText(d.get("mov_max", ""))
        if idx_min >= 0: self.mov_min_cb.setCurrentIndex(idx_min)
        if idx_max >= 0: self.mov_max_cb.setCurrentIndex(idx_max)

    def _guardar(self):
        mn = self.min_sb.value()
        mx = self.max_sb.value()
        if mn >= mx:
            QMessageBox.warning(
                self, "Error en ticks",
                f"Mín ticks ({mn}) debe ser menor que Máx ticks ({mx}).")
            return

        nombre = self.nombre_le.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Campo requerido",
                                "Escribe un nombre para el servo.")
            return

        pca   = int(self.pca_cb.currentText())
        canal = int(self.canal_cb.currentText())
        ubicacion  = self.ubic_cb.currentText()
        nombre_corto = generar_nombre_corto(ubicacion, nombre)

        self.data.setdefault(pca, {})[canal] = {
            "nombre":       nombre,
            "nombre_corto": nombre_corto,
            "ubicacion":    ubicacion,
            "modelo":       self.modelo_cb.currentText(),
            "voltaje":      self.voltaje_lbl.text(),
            "min":          mn,
            "max":          mx,
            "centro":       (mn + mx) // 2,
            "mov_min":      self.mov_min_cb.currentText(),
            "mov_max":      self.mov_max_cb.currentText(),
        }

        guardar_datos(self.data)
        self.servo_guardado.emit()
        self._reset_modo()

        QMessageBox.information(
            self, "Guardado",
            f"✅  {nombre_corto}\n"
            f"PCA {pca} · Canal {canal}\n"
            f"Guardado en:\n{SERVO_FILE}"
        )

# ─── PANEL ÁRBOL (lista de servos) ────────────────────────────────────────────
class ArbolPanel(QWidget):
    def __init__(self, data, form):
        super().__init__()
        self.data = data
        self.form = form
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        title = QLabel("Servos configurados")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #3a4a8a;")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Canal", "Nombre", "Ubicación"])
        self.tree.setColumnWidth(0, 55)
        self.tree.setColumnWidth(1, 120)
        self.tree.setColumnWidth(2, 100)
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 2px solid #a0b8ff;
                border-radius: 8px;
                background: white;
                font-size: 11px;
            }
            QTreeWidget::item:selected {
                background: #c8d8ff;
                color: black;
            }
            QHeaderView::section {
                background: #d8e0ff;
                font-weight: bold;
                border: none;
                padding: 4px;
            }
        """)
        self.tree.itemClicked.connect(self._on_click)
        lay.addWidget(self.tree)

        btn_edit = QPushButton("✏️  Editar servo")
        estilo_boton(btn_edit, "#ffe0b3")
        btn_edit.clicked.connect(self._editar)
        lay.addWidget(btn_edit)

        btn_del = QPushButton("🗑  Eliminar servo")
        estilo_boton(btn_del, "#ffb3b3")
        btn_del.clicked.connect(self._eliminar)
        lay.addWidget(btn_del)

        self.lbl_ruta = QLabel(f"📂 {SERVO_FILE}")
        self.lbl_ruta.setStyleSheet("font-size: 9px; color: #6070a0;")
        self.lbl_ruta.setWordWrap(True)
        lay.addWidget(self.lbl_ruta)

        self.refresh()

    def refresh(self):
        self.tree.clear()
        for pca in sorted(self.data.keys()):
            pca_item = QTreeWidgetItem(self.tree, [f"PCA {pca}", "", ""])
            pca_item.setFlags(pca_item.flags() & ~Qt.ItemIsSelectable)
            pca_item.setForeground(0, QBrush(QColor("#3a4a8a")))
            font = pca_item.font(0)
            font.setBold(True)
            pca_item.setFont(0, font)
            pca_item.setData(0, Qt.UserRole, ("pca", pca))

            for canal in sorted(self.data[pca].keys()):
                d = self.data[pca][canal]
                ch_item = QTreeWidgetItem(pca_item, [
                    str(canal),
                    d.get("nombre", "—"),
                    d.get("ubicacion", "—"),
                ])
                ch_item.setData(0, Qt.UserRole, ("servo", pca, canal))
                mn  = d.get("min", "—")
                mx  = d.get("max", "—")
                tt = (
                    f"Modelo: {d.get('modelo','—')}\n"
                    f"Voltaje: {d.get('voltaje','—')}\n"
                    f"Min: {mn}  Max: {mx}  Centro: {d.get('centro','—')}\n"
                    f"Mov {mn}→{mx}: {d.get('mov_min','—')}\n"
                    f"Mov {mx}→{mn}: {d.get('mov_max','—')}"
                )
                for col in range(3):
                    ch_item.setToolTip(col, tt)

            pca_item.setExpanded(True)

    def _pca_canal_seleccionado(self):
        item = self.tree.currentItem()
        if not item:
            return None
        d = item.data(0, Qt.UserRole)
        if d and d[0] == "servo":
            return d[1], d[2]   # pca, canal
        return None

    def _on_click(self, item):
        """Solo resalta — editar requiere botón explícito."""
        pass

    def _editar(self):
        sel = self._pca_canal_seleccionado()
        if sel is None:
            QMessageBox.information(self, "Editar", "Selecciona un servo de la lista.")
            return
        pca, canal = sel
        self.form.cargar_servo(pca, canal)
        self.form._modo_edicion = True
        self.form._bloquear_campos(False)
        self.form.pca_cb.setEnabled(False)
        self.form.canal_cb.setEnabled(False)
        self.form.lbl_aviso.setText("✏️  Modo edición — modifica los campos y guarda.")
        self.form.lbl_aviso.setStyleSheet(
            "font-size: 11px; color: #1a6a20; font-weight: bold;")
        self.form.btn_guardar.setVisible(True)
        self.form.btn_editar.setVisible(False)

    def _eliminar(self):
        sel = self._pca_canal_seleccionado()
        if sel is None:
            QMessageBox.information(self, "Eliminar", "Selecciona un servo de la lista.")
            return
        pca, canal = sel
        nombre = self.data[pca][canal].get("nombre", "")
        resp = QMessageBox.question(
            self, "Eliminar",
            f"¿Eliminar '{nombre}' (PCA {pca} · Canal {canal})?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp == QMessageBox.Yes:
            del self.data[pca][canal]
            if not self.data[pca]:
                del self.data[pca]
            guardar_datos(self.data)
            self.refresh()

# ─── VENTANA PRINCIPAL ────────────────────────────────────────────────────────
class EditorServo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("R-ONE  ·  Editor de Servos")
        self.setGeometry(0, 0, 820, 560)

        self.data = cargar_datos()

        # ── Widgets ──
        self.form  = FormPanel(self.data)
        self.arbol = ArbolPanel(self.data, self.form)

        self.form.servo_guardado.connect(self.arbol.refresh)

        # ── Scroll para el form ──
        scroll = QScrollArea()
        scroll.setWidget(self.form)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 8px; background: transparent; }
            QScrollBar::handle:vertical { background: #a0b8ff; border-radius: 4px; min-height: 20px; }
            QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
        """)

        # ── Splitter ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(scroll)
        splitter.addWidget(self.arbol)
        splitter.setSizes([460, 340])
        splitter.setStyleSheet("QSplitter::handle { background: #c0caff; width: 3px; }")

        header = QLabel("⚙  Editor de PCA9685 / Servos  —  R-ONE")
        header.setAlignment(Qt.AlignCenter)
        header.setFixedHeight(24)
        header.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #b8c6ff, stop:1 #d6b3ff);
            font-size: 10px;
            font-weight: bold;
            color: #2a3a7a;
            padding: 2px;
            border-radius: 0px;
        """)

        root = QWidget()
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(header)
        lay.addWidget(splitter)

        self.setCentralWidget(root)

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, lambda: None)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    aplicar_tema(app)
    w = EditorServo()
    w.show()
    sys.exit(app.exec_())
