const test = require("node:test");
const assert = require("node:assert/strict");
const {
  groupLibraryItems,
  blockCardText,
  formatArduinoStatus,
  NEUTRO_REVIEW_WARNING,
} = require("../src/static/library-view.js");

test("groups by category and wraps unknown", () => {
  const groups = groupLibraryItems([
    { name: "largo-nombre-de-abrazo-izquierdo", category: "brazo_izquierdo" },
    { name: "sin", category: null },
  ]);
  assert.equal(groups[0].label, "brazo_izquierdo");
  assert.equal(groups[0].items[0].name, "largo-nombre-de-abrazo-izquierdo");
  assert.equal(groups.at(-1).label, "Sin categoría");
});

test("card text lists every block field", () => {
  const text = blockCardText({
    nombre: "P0_S1",
    pca: 1,
    servo: 14,
    inicio: 0,
    dur: 2,
    pos: 650,
    vel: 3,
    arduino_id: 1,
  });
  for (const token of ["P0_S1", "pca:1", "s:14", "t:0", "d:2", "pos:650", "v:3", "ard:1"]) {
    assert.ok(text.includes(token), `missing ${token} in ${text}`);
  }
});

test("card omits arduino when 0", () => {
  const text = blockCardText({
    nombre: "P0_S1",
    pca: 0,
    servo: 1,
    inicio: 1,
    dur: 1,
    pos: 1,
    vel: 1,
    arduino_id: 0,
  });
  assert.ok(!text.includes("ard:"));
});

test("card omits arduino when missing", () => {
  const text = blockCardText({
    nombre: "P0_S1",
    pca: 0,
    servo: 0,
    inicio: 0,
    dur: 2,
    pos: 500,
    vel: 5,
  });
  assert.ok(!text.includes("ard:"));
  assert.ok(!text.includes("undefined"));
});

test("warning copy is locked", () => {
  assert.equal(
    NEUTRO_REVIEW_WARNING,
    "El neutro generado debe revisarlo una persona. En el androide no es fiable.",
  );
});

test("arduino status matches the panel", () => {
  assert.deepEqual(formatArduinoStatus([]), { connected: false, label: "Sin Arduino" });
  assert.deepEqual(formatArduinoStatus([{ arduino_id: 1, port: "/dev/ttyUSB0" }]), {
    connected: true,
    label: "Arduino #1 · /dev/ttyUSB0",
  });
});
