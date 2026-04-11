#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// ── 4 módulos PCA9685 en direcciones I2C 0x40–0x43 ──
Adafruit_PWMServoDriver pca0 = Adafruit_PWMServoDriver(0x40);
Adafruit_PWMServoDriver pca1 = Adafruit_PWMServoDriver(0x41);
Adafruit_PWMServoDriver pca2 = Adafruit_PWMServoDriver(0x42);
Adafruit_PWMServoDriver pca3 = Adafruit_PWMServoDriver(0x43);

// ── Rango PWM (ajusta según tus servos) ──
#define SERVOMIN 100   // pulso mínimo (~0°)
#define SERVOMAX 500   // pulso máximo (~180°)

// ── Estado de cada servo: [pca][canal] ──
struct ServoData {
  int actual = 300;
  int target = 300;
  int speed  = 5;
};

ServoData servos[4][16];

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

void setup() {
  Serial.begin(115200);

  pca0.begin(); pca0.setPWMFreq(50);
  pca1.begin(); pca1.setPWMFreq(50);
  pca2.begin(); pca2.setPWMFreq(50);
  pca3.begin(); pca3.setPWMFreq(50);
}

void loop() {
  leerSerial();
  actualizarServos();
}

// ── Recibe comandos: "PCA,<pca>,<canal>,<pos 0-1000>,<vel 1-10>\n" ──
void leerSerial() {
  while (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    int pca, ch, pos, vel;
    if (sscanf(cmd.c_str(), "PCA,%d,%d,%d,%d", &pca, &ch, &pos, &vel) == 4) {
      // Validar rangos
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
  for (int p = 0; p < 4; p++) {          // ← 4 PCAs
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
