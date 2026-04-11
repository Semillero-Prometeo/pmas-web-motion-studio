#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// ════════════════════════════════════════════════════════
//  R-ONE / InMoov — Control 4x PCA9685 + Arduino Mega
//
//  PCA 0 (0x40) — Brazo derecho   10x DS5160 @ 7V
//  PCA 1 (0x41) — Brazo izquierdo 10x DS5160 @ 7V
//  PCA 2 (0x42) — Torso y cuello   6x DS5160 @ 7V
//  PCA 3 (0x43) — Cabeza          14x SG90   @ 5V
// ════════════════════════════════════════════════════════

Adafruit_PWMServoDriver pca0 = Adafruit_PWMServoDriver(0x40);
Adafruit_PWMServoDriver pca1 = Adafruit_PWMServoDriver(0x41);
Adafruit_PWMServoDriver pca2 = Adafruit_PWMServoDriver(0x42);
Adafruit_PWMServoDriver pca3 = Adafruit_PWMServoDriver(0x43);

// ── Rango PWM por PCA ──────────────────────────────────
//  DS5160 @ 7V  → pulso 1.0–2.0 ms conservador
//                 sube SERVOMAX_DS de 10 en 10 si el brazo
//                 no llega a la posición deseada (máx ~500)
//  SG90   @ 5V  → pulso estándar 1.0–2.0 ms
//
//  Fórmula: ticks = (ms / 20ms) × 4096
//    1.0 ms → 205    1.5 ms → 307    2.0 ms → 410
// ──────────────────────────────────────────────────────
#define SERVOMIN_DS  205   // DS5160 mínimo  (~1.0 ms)
#define SERVOMAX_DS  450   // DS5160 máximo  (~2.2 ms) — ajustar si falta rango
#define SERVOMIN_SG  150   // SG90 mínimo    (~0.73 ms)
#define SERVOMAX_SG  600   // SG90 máximo    (~2.93 ms)

// ── Intervalo de actualización de servos (ms) ─────────
#define SERVO_INTERVAL_MS 10

// ── Estado de cada servo: [pca][canal] ────────────────
struct ServoData {
  int actual = 307;   // arranca en centro (~1.5 ms)
  int target = 307;
  int speed  = 5;
};

ServoData servos[4][16];

// ── Direcciones I2C de cada PCA ───────────────────────
const uint8_t PCA_ADDR[4] = {0x40, 0x41, 0x42, 0x43};
bool pca_presente[4] = {false, false, false, false};

// ── Retorna puntero al PCA correcto ───────────────────
Adafruit_PWMServoDriver* getPCA(int id) {
  switch (id) {
    case 0: return &pca0;
    case 1: return &pca1;
    case 2: return &pca2;
    case 3: return &pca3;
    default: return &pca0;
  }
}

// ── Convierte posición 0–1000 a ticks PWM según PCA ──
//    PCA 0,1,2 → DS5160    PCA 3 → SG90
int mapPos(int pca, int pos) {
  if (pca == 3)
    return map(pos, 0, 1000, SERVOMIN_SG, SERVOMAX_SG);
  else
    return map(pos, 0, 1000, SERVOMIN_DS, SERVOMAX_DS);
}

// ── Detecta qué PCAs responden en el bus I2C ──────────
void escanearPCAs() {
  for (int i = 0; i < 4; i++) {
    Wire.beginTransmission(PCA_ADDR[i]);
    pca_presente[i] = (Wire.endTransmission() == 0);
  }
}

// ── Reporta PCAs detectadas por serial ────────────────
// Formato: "PCAS:0,1,2,3"  (solo los índices conectados)
void reportarPCAs() {
  String resp = "PCAS:";
  bool primero = true;
  for (int i = 0; i < 4; i++) {
    if (pca_presente[i]) {
      if (!primero) resp += ",";
      resp += String(i);
      primero = false;
    }
  }
  Serial.println(resp);
}

// ── Centra todos los servos al arrancar ───────────────
void centrarTodos() {
  for (int p = 0; p < 4; p++) {
    if (!pca_presente[p]) continue;
    int centro = mapPos(p, 500);
    for (int ch = 0; ch < 16; ch++) {
      servos[p][ch].actual = centro;
      servos[p][ch].target = centro;
      getPCA(p)->setPWM(ch, 0, centro);
    }
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(100000);  // I2C modo fast — importante con 4 PCAs

  // Escanear e inicializar solo las PCAs presentes
  escanearPCAs();
  if (pca_presente[0]) { pca0.begin(); pca0.setPWMFreq(50); }
  if (pca_presente[1]) { pca1.begin(); pca1.setPWMFreq(50); }
  if (pca_presente[2]) { pca2.begin(); pca2.setPWMFreq(50); }
  if (pca_presente[3]) { pca3.begin(); pca3.setPWMFreq(50); }

  // Llevar todos los servos al centro antes de reportar
  centrarTodos();

  // Reportar PCAs conectadas al arrancar
  reportarPCAs();
}

void loop() {
  leerSerial();
  actualizarServos();
}

// ── Recibe comandos ────────────────────────────────────
//   "PCA,<pca>,<canal>,<pos 0-1000>,<vel 1-10>\n"
//   "SCAN\n"    → re-escanear y reportar PCAs
//   "CENTER\n"  → centrar todos los servos
// ──────────────────────────────────────────────────────
void leerSerial() {
  while (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "SCAN") {
      escanearPCAs();
      reportarPCAs();
      return;
    }

    if (cmd == "CENTER") {
      centrarTodos();
      return;
    }

    int pca, ch, pos, vel;
    if (sscanf(cmd.c_str(), "PCA,%d,%d,%d,%d", &pca, &ch, &pos, &vel) == 4) {
      if (pca >= 0 && pca <= 3 && ch >= 0 && ch <= 15 &&
          pos >= 0 && pos <= 1000 && vel >= 1 && vel <= 10) {
        servos[pca][ch].target = mapPos(pca, pos);
        servos[pca][ch].speed  = vel;
      }
    }
  }
}

// ── Mueve cada servo un paso hacia su target ──────────
//    Timer no bloqueante: no usa delay(), el loop() sigue
//    leyendo serial mientras los servos se mueven.
//    Crítico con 40 servos activos simultáneamente.
// ──────────────────────────────────────────────────────
void actualizarServos() {
  static unsigned long ultimo = 0;
  unsigned long ahora = millis();
  if (ahora - ultimo < SERVO_INTERVAL_MS) return;
  ultimo = ahora;

  for (int p = 0; p < 4; p++) {
    if (!pca_presente[p]) continue;

    for (int ch = 0; ch < 16; ch++) {
      int &actual = servos[p][ch].actual;
      int  target = servos[p][ch].target;
      int  vel    = servos[p][ch].speed;

      if (abs(actual - target) > 2) {
        int step = max(1, vel);
        if (actual < target) actual += step;
        else                 actual -= step;
        getPCA(p)->setPWM(ch, 0, actual);
      }
    }
  }
}
