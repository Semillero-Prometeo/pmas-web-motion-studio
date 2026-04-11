#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// ── 4 módulos PCA9685 en direcciones I2C 0x40–0x43 ──
Adafruit_PWMServoDriver pca0 = Adafruit_PWMServoDriver(0x40);
Adafruit_PWMServoDriver pca1 = Adafruit_PWMServoDriver(0x41);
Adafruit_PWMServoDriver pca2 = Adafruit_PWMServoDriver(0x42);
Adafruit_PWMServoDriver pca3 = Adafruit_PWMServoDriver(0x43);

// ── Rango PWM (ajusta según tus servos) ──
#define SERVOMIN 100
#define SERVOMAX 500

// ── Estado de cada servo: [pca][canal] ──
struct ServoData {
  int actual = 300;
  int target = 300;
  int speed  = 5;
};

ServoData servos[4][16];

// ── Direcciones I2C de cada PCA ──
const uint8_t PCA_ADDR[4] = {0x40, 0x41, 0x42, 0x43};
bool pca_presente[4] = {false, false, false, false};

// ── Retorna puntero al PCA correcto ──
Adafruit_PWMServoDriver* getPCA(int id) {
  switch (id) {
    case 0: return &pca0;
    case 1: return &pca1;
    case 2: return &pca2;
    case 3: return &pca3;
    default: return &pca0;
  }
}

// ── Convierte posición 0–1000 a ticks PWM ──
int mapPos(int pos) {
  return map(pos, 0, 1000, SERVOMIN, SERVOMAX);
}

// ── Detecta qué PCAs responden en el bus I2C ──
void escanearPCAs() {
  for (int i = 0; i < 4; i++) {
    Wire.beginTransmission(PCA_ADDR[i]);
    pca_presente[i] = (Wire.endTransmission() == 0);
  }
}

// ── Reporta PCAs detectadas por serial ──
// Formato: "PCAS:0,1,3"  (solo los índices conectados)
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

void setup() {
  Serial.begin(115200);
  Wire.begin();

  // Escanear e inicializar solo las PCAs presentes
  escanearPCAs();
  if (pca_presente[0]) { pca0.begin(); pca0.setPWMFreq(50); }
  if (pca_presente[1]) { pca1.begin(); pca1.setPWMFreq(50); }
  if (pca_presente[2]) { pca2.begin(); pca2.setPWMFreq(50); }
  if (pca_presente[3]) { pca3.begin(); pca3.setPWMFreq(50); }

  // Reportar PCAs conectadas al arrancar
  reportarPCAs();
}

void loop() {
  leerSerial();
  actualizarServos();
}

// ── Recibe comandos:
//    "PCA,<pca>,<canal>,<pos 0-1000>,<vel 1-10>\n"
//    "SCAN\n"  → re-escanear y reportar PCAs
// ──
void leerSerial() {
  while (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "SCAN") {
      escanearPCAs();
      reportarPCAs();
      return;
    }

    int pca, ch, pos, vel;
    if (sscanf(cmd.c_str(), "PCA,%d,%d,%d,%d", &pca, &ch, &pos, &vel) == 4) {
      if (pca >= 0 && pca <= 3 && ch >= 0 && ch <= 15 &&
          pos >= 0 && pos <= 1000 && vel >= 1 && vel <= 10) {
        servos[pca][ch].target = mapPos(pos);
        servos[pca][ch].speed  = vel;
      }
    }
  }
}

// ── Mueve cada servo un paso hacia su target ──
void actualizarServos() {
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
  delay(10);
}
