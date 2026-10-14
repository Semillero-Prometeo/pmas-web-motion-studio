const POST_AUTH = "prometeo-auth";
const POST_AUTH_REQUEST = "prometeo-auth-request";
const PX = 100;
const ROW_H = 44;
const SECONDS = 41;
const COLORS = ["#7aa0ff", "#5fd08a", "#ffb45c", "#c98cff", "#ff7a7a"];
const COLORS_OVERLAP = ["#3d5bb5", "#2d8a52", "#c47a28", "#7a3fb0", "#c43a3a"];

let token = null;
let gatewayUrl = null;
let blocks = [];
let selectedId = null;
let nextId = 1;
let playing = false;
let playStartedAt = 0;
let playFrame = 0;
let drag = null;
let libraryItems = [];
let selectedLibraryName = null;

const els = {
  name: document.getElementById("name"),
  description: document.getElementById("description"),
  arduino: document.getElementById("arduino_id"),
  mode: document.getElementById("mode"),
  status: document.getElementById("status"),
  lanes: document.getElementById("lanes"),
  tracks: document.getElementById("tracks"),
  ruler: document.getElementById("ruler"),
  stage: document.getElementById("stage"),
  playhead: document.getElementById("playhead"),
  inspector: document.getElementById("inspector"),
  librarySource: document.getElementById("library-source"),
  libraryList: document.getElementById("library-list"),
};

if (window.self !== window.top || new URLSearchParams(location.search).has("embed")) {
  document.documentElement.classList.add("embedded");
}

function isTrustedParent(event) {
  try {
    return new URL(event.origin).hostname === window.location.hostname;
  } catch {
    return false;
  }
}

window.addEventListener("message", (event) => {
  if (!isTrustedParent(event)) return;
  const data = event.data || {};
  if (data.type !== POST_AUTH) return;
  if (typeof data.token !== "string" || !data.token) return;
  if (typeof data.gatewayUrl !== "string" || !data.gatewayUrl) return;
  token = data.token;
  gatewayUrl = data.gatewayUrl.replace(/\/$/, "");
  els.mode.textContent = "Acoplado";
  setStatus("Acoplado a robótica");
  refreshLibrary();
});

function isCoupled() {
  return Boolean(token && gatewayUrl);
}

function setStatus(message, isError = false) {
  els.status.textContent = message;
  els.status.classList.toggle("error", isError);
}

function roundTime(value) {
  return Math.max(0, Math.round(Number(value) * 100) / 100);
}

function nextServo() {
  const used = new Set(blocks.map((block) => `${block.pca}:${block.servo}`));
  for (let pca = 0; pca < 3; pca += 1) {
    for (let servo = 0; servo < 16; servo += 1) {
      if (!used.has(`${pca}:${servo}`)) return { pca, servo };
    }
  }
  return { pca: 0, servo: 0 };
}

function createBlock(partial = {}) {
  const servo = nextServo();
  const block = {
    id: nextId,
    pca: servo.pca,
    servo: servo.servo,
    inicio: 0,
    dur: 2,
    pos: 500,
    vel: 5,
    nombre: `P${servo.pca}_S${servo.servo}`,
    ...partial,
  };
  nextId += 1;
  if (partial.pca === undefined || partial.servo === undefined) {
    block.nombre = `P${block.pca}_S${block.servo}`;
  }
  return block;
}

function lanesOf(list) {
  const keys = [...new Set(list.map((block) => `${block.pca}:${block.servo}`))];
  keys.sort((a, b) => {
    const [pcaA, servoA] = a.split(":").map(Number);
    const [pcaB, servoB] = b.split(":").map(Number);
    return pcaA - pcaB || servoA - servoB;
  });
  return keys.map((key) => {
    const [pca, servo] = key.split(":").map(Number);
    return { key, pca, servo };
  });
}

function overlaps(a, b) {
  return a.inicio < b.inicio + b.dur && a.inicio + a.dur > b.inicio;
}

function drawRuler() {
  els.ruler.style.width = `${SECONDS * PX}px`;
  els.ruler.innerHTML = "";
  for (let second = 0; second < SECONDS; second += 1) {
    const tick = document.createElement("div");
    tick.className = "tick";
    tick.textContent = `${second}s`;
    els.ruler.appendChild(tick);
  }
}

function render() {
  const lanes = lanesOf(blocks);
  els.lanes.innerHTML = "";
  els.tracks.innerHTML = "";
  els.tracks.style.width = `${SECONDS * PX}px`;
  els.tracks.style.minHeight = `${Math.max(lanes.length, 4) * ROW_H}px`;
  els.tracks.style.height = "";

  const rowCount = Math.max(lanes.length, 8);
  for (let row = 0; row < rowCount; row += 1) {
    const lane = lanes[row];
    const label = document.createElement("div");
    label.className = "lane";
    label.textContent = lane ? `PCA ${lane.pca} · S${lane.servo}` : "";
    els.lanes.appendChild(label);

    const rowEl = document.createElement("div");
    rowEl.className = "row";
    rowEl.dataset.row = String(row);
    if (lane) {
      const rowBlocks = blocks
        .filter((block) => block.pca === lane.pca && block.servo === lane.servo)
        .sort((a, b) => a.inicio - b.inicio);
      rowBlocks.forEach((block, order) => {
        const overlapping = rowBlocks.some((other) => other.id !== block.id && overlaps(block, other));
        const el = document.createElement("div");
        el.className = "block" + (block.id === selectedId ? " selected" : "");
        el.dataset.id = String(block.id);
        el.setAttribute("role", "button");
        el.setAttribute("aria-label", block.nombre);
        el.tabIndex = 0;
        el.style.left = `${block.inicio * PX}px`;
        el.style.width = `${Math.max(block.dur * PX, 24)}px`;
        el.style.background = overlapping
          ? COLORS_OVERLAP[(row + order) % COLORS.length]
          : COLORS[(row + order) % COLORS.length];
        el.innerHTML = `<span>${block.nombre}  Pos:${block.pos} V:${block.vel}</span><button type="button" class="kill" aria-label="Eliminar">×</button><span class="resize"></span>`;
        rowEl.appendChild(el);
      });
    } else if (row === 0) {
      rowEl.style.color = "#b8c4ce";
      rowEl.style.display = "flex";
      rowEl.style.alignItems = "center";
      rowEl.style.paddingLeft = "12px";
      rowEl.style.fontSize = "0.78rem";
      rowEl.textContent = "Agregar coloca el primer servo en la línea de tiempo.";
    }
    els.tracks.appendChild(rowEl);
  }

  syncInspector();
}

function findBlock(id) {
  return blocks.find((block) => block.id === id);
}

function selectBlock(id) {
  selectedId = id;
  render();
}

function syncInspector() {
  const block = findBlock(selectedId);
  els.inspector.hidden = !block;
  if (!block) return;
  document.getElementById("edit-nombre").value = block.nombre;
  document.getElementById("edit-pca").value = block.pca;
  document.getElementById("edit-servo").value = block.servo;
  document.getElementById("edit-pos").value = block.pos;
  document.getElementById("edit-vel").value = block.vel;
  document.getElementById("edit-dur").value = block.dur;
}

function applyInspector() {
  const block = findBlock(selectedId);
  if (!block) return;
  block.nombre = document.getElementById("edit-nombre").value.slice(0, 80);
  block.pca = Number(document.getElementById("edit-pca").value);
  block.servo = Number(document.getElementById("edit-servo").value);
  block.pos = Number(document.getElementById("edit-pos").value);
  block.vel = Number(document.getElementById("edit-vel").value);
  block.dur = Math.max(0.1, Number(document.getElementById("edit-dur").value) || 0.1);
  render();
}

function deleteSelected() {
  if (selectedId == null) return;
  blocks = blocks.filter((block) => block.id !== selectedId);
  selectedId = null;
  render();
}

function buildOrigin() {
  return {
    name: els.name.value.trim(),
    description: els.description.value.replace(/\n/g, " ").slice(0, 280),
    arduino_id: Number(els.arduino.value || 0),
    blocks: blocks.map((block) => [
      Number(block.pca),
      Number(block.servo),
      roundTime(block.inicio),
      Number(block.dur),
      Number(block.pos),
      Number(block.vel),
      String(block.nombre),
    ]),
  };
}

async function authorizedFetch(path, options = {}) {
  const response = await fetch(`${gatewayUrl}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });
  if (response.status === 401 || response.status === 403) {
    token = null;
    els.mode.textContent = "Suelto: no hay sesión";
    window.parent.postMessage({ type: POST_AUTH_REQUEST }, "*");
    throw new Error("Sesión vencida");
  }
  return response;
}

async function readError(response) {
  const text = await response.text();
  try {
    const json = JSON.parse(text);
    if (typeof json.detail === "string") return json.detail;
  } catch {
    /* plain text from gateway */
  }
  return text;
}

function localSequenceUrl(name) {
  return `/local/sequences/${name.split("/").map(encodeURIComponent).join("/")}`;
}

function renderLibrary() {
  const coupled = isCoupled();
  els.librarySource.textContent = coupled ? "Robótica" : "Disco";
  els.libraryList.innerHTML = "";
  if (!libraryItems.length) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = coupled ? "No hay secuencias en robótica." : "No hay secuencias en disco.";
    els.libraryList.appendChild(empty);
    return;
  }
  libraryItems.forEach((item) => {
    const row = document.createElement("li");
    row.className = "lib-item";
    const open = document.createElement("button");
    open.type = "button";
    open.className = "lib-open" + (item.name === selectedLibraryName ? " active" : "");
    open.dataset.name = item.name;
    const title = document.createElement("strong");
    title.textContent = item.name;
    const meta = document.createElement("span");
    const bits = [];
    if (item.id != null) bits.push(`#${item.id}`);
    if (item.description) bits.push(item.description);
    meta.textContent = bits.join(" · ") || "Sin descripción";
    open.append(title, meta);
    open.onclick = () => openSequence(item.name);
    const play = document.createElement("button");
    play.type = "button";
    play.className = "btn btn-play lib-play";
    play.textContent = "Play";
    play.setAttribute("aria-label", `Reproducir ${item.name}`);
    play.onclick = (event) => {
      event.stopPropagation();
      playSequence(item.name);
    };
    row.append(open, play);
    els.libraryList.appendChild(row);
  });
}

async function refreshLibrary() {
  try {
    if (isCoupled()) {
      const response = await authorizedFetch("/sequence/files");
      if (!response.ok) throw new Error(await readError(response) || "No se pudo listar");
      const payload = await response.json();
      libraryItems = payload.data || [];
    } else {
      const response = await fetch("/local/sequences");
      if (!response.ok) throw new Error("No se pudo listar el disco");
      const payload = await response.json();
      libraryItems = payload.data || [];
    }
    renderLibrary();
  } catch (error) {
    libraryItems = [];
    renderLibrary();
    setStatus(error.message || "No se pudo listar", true);
  }
}

async function fetchSequence(name) {
  if (isCoupled()) {
    const response = await authorizedFetch(`/sequence/file?name=${encodeURIComponent(name)}`);
    if (!response.ok) throw new Error(await readError(response) || "No se pudo abrir");
    return response.json();
  }
  const response = await fetch(localSequenceUrl(name));
  if (!response.ok) throw new Error(await readError(response) || "No se pudo abrir");
  return response.json();
}

async function openSequence(name) {
  try {
    parseLoadedSequence(await fetchSequence(name));
    selectedLibraryName = name;
    renderLibrary();
    setStatus(`Editando: ${name}`);
  } catch (error) {
    setStatus(error.message || "No se pudo abrir", true);
  }
}

async function playSequence(name) {
  await openSequence(name);
  await playCurrent();
}

async function saveLocal(overwrite) {
  const sequence = buildOrigin();
  const response = await fetch("/local/sequences", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sequence, overwrite: Boolean(overwrite) }),
  });
  if (response.status === 409 && !overwrite) {
    if (confirm("La secuencia ya existe. ¿Sobrescribir?")) {
      return saveLocal(true);
    }
    return false;
  }
  if (!response.ok) {
    throw new Error(await readError(response) || "No se pudo guardar");
  }
  return true;
}

async function saveCoupled(overwrite) {
  const sequence = buildOrigin();
  const response = await authorizedFetch("/sequence/file", {
    method: "POST",
    body: JSON.stringify({ sequence, overwrite: Boolean(overwrite) }),
  });
  if (!response.ok) {
    const text = await readError(response);
    if (!overwrite && /ya existe/i.test(text)) {
      if (confirm("La secuencia ya existe. ¿Sobrescribir?")) {
        return saveCoupled(true);
      }
      return false;
    }
    throw new Error("No se pudo guardar");
  }
  return true;
}

async function playCurrent() {
  const sequence = buildOrigin();
  if (!sequence.blocks.length) {
    setStatus("Agrega al menos un bloque", true);
    return;
  }
  if (playing) {
    setStatus("Ya hay una secuencia en curso. Presiona Stop.", true);
    return;
  }
  startPlayhead();
  if (!isCoupled()) {
    setStatus("Línea de tiempo en curso (suelto)");
    return;
  }
  const playBlocks = sequence.blocks.map((item) => ({
    arduino_id: sequence.arduino_id,
    pca: item[0],
    servo: item[1],
    inicio: item[2],
    dur: item[3],
    pos: item[4],
    vel: item[5],
    nombre: item[6],
  }));
  try {
    const response = await authorizedFetch("/sequence/play", {
      method: "POST",
      body: JSON.stringify({ blocks: playBlocks }),
    });
    if (!response.ok) throw new Error("No se pudo previsualizar");
    setStatus("Previsualización en curso");
  } catch (error) {
    setStatus(error.message || "No se pudo previsualizar", true);
  }
}

function totalDuration() {
  return blocks.reduce((max, block) => Math.max(max, block.inicio + block.dur), 0);
}

function setPlayhead(time, visible) {
  els.playhead.hidden = !visible;
  els.playhead.style.left = `${time * PX}px`;
  if (visible) {
    const target = time * PX - els.stage.clientWidth / 2;
    els.stage.scrollLeft = Math.max(0, target);
  }
}

function tickPlayhead(now) {
  if (!playing) return;
  const time = (now - playStartedAt) / 1000;
  const end = Math.max(totalDuration(), 0.2);
  setPlayhead(time, true);
  if (time >= end) {
    stopPlayhead();
    return;
  }
  playFrame = requestAnimationFrame(tickPlayhead);
}

function startPlayhead() {
  playing = true;
  playStartedAt = performance.now();
  setPlayhead(0, true);
  playFrame = requestAnimationFrame(tickPlayhead);
}

function stopPlayhead() {
  playing = false;
  cancelAnimationFrame(playFrame);
  setPlayhead(0, false);
}

function replaceBlocks(nextBlocks) {
  blocks = nextBlocks.map((item) => createBlock(item));
  selectedId = null;
  render();
}

function parseLoadedSequence(payload) {
  const sequence = payload.sequence || payload;
  els.name.value = sequence.name || "";
  els.description.value = sequence.description || "";
  const rawBlocks = Array.isArray(sequence.blocks) ? sequence.blocks : [];
  const mapped = rawBlocks.map((item) => {
    if (Array.isArray(item)) {
      return {
        pca: item[0],
        servo: item[1],
        inicio: item[2],
        dur: item[3],
        pos: item[4],
        vel: item[5],
        nombre: item[6],
      };
    }
    return {
      pca: item.pca,
      servo: item.servo,
      inicio: item.inicio,
      dur: item.dur,
      pos: item.pos,
      vel: item.vel,
      nombre: item.nombre,
    };
  });
  if (sequence.arduino_id != null) {
    els.arduino.value = sequence.arduino_id;
  } else if (rawBlocks[0] && !Array.isArray(rawBlocks[0]) && rawBlocks[0].arduino_id != null) {
    els.arduino.value = rawBlocks[0].arduino_id;
  }
  replaceBlocks(mapped);
}

els.tracks.addEventListener("pointerdown", (event) => {
  const kill = event.target.closest(".kill");
  if (kill) {
    const id = Number(kill.closest(".block").dataset.id);
    blocks = blocks.filter((block) => block.id !== id);
    if (selectedId === id) selectedId = null;
    render();
    return;
  }

  const handle = event.target.closest(".resize");
  const node = event.target.closest(".block");
  if (!node) {
    selectedId = null;
    render();
    return;
  }

  const block = findBlock(Number(node.dataset.id));
  if (!block) return;
  selectedId = block.id;
  els.tracks.querySelectorAll(".block").forEach((el) => {
    el.classList.toggle("selected", Number(el.dataset.id) === block.id);
  });
  syncInspector();
  const lanes = lanesOf(blocks);
  const row = lanes.findIndex((lane) => lane.pca === block.pca && lane.servo === block.servo);
  drag = {
    id: block.id,
    mode: handle ? "resize" : "move",
    startX: event.clientX,
    startY: event.clientY,
    origInicio: block.inicio,
    origDur: block.dur,
    origRow: Math.max(row, 0),
  };
  node.setPointerCapture(event.pointerId);
});

els.tracks.addEventListener("pointermove", (event) => {
  if (!drag) return;
  const block = findBlock(drag.id);
  if (!block) return;
  const dx = event.clientX - drag.startX;
  if (drag.mode === "resize") {
    block.dur = Math.max(0.1, roundTime(drag.origDur + dx / PX));
  } else {
    block.inicio = roundTime(drag.origInicio + dx / PX);
    const node = els.tracks.querySelector(`.block[data-id="${block.id}"]`);
    if (node) {
      const dy = event.clientY - drag.startY;
      node.style.top = `${7 + dy}px`;
      node.style.left = `${block.inicio * PX}px`;
      node.style.width = `${Math.max(block.dur * PX, 24)}px`;
    }
    return;
  }
  const node = els.tracks.querySelector(`.block[data-id="${block.id}"]`);
  if (node) {
    node.style.width = `${Math.max(block.dur * PX, 24)}px`;
  }
});

els.tracks.addEventListener("pointerup", (event) => {
  if (!drag) return;
  const block = findBlock(drag.id);
  const current = drag;
  drag = null;
  if (!block || current.mode !== "move") {
    render();
    syncInspector();
    return;
  }
  const lanes = lanesOf(blocks);
  const dest = Math.max(0, Math.round(current.origRow + (event.clientY - current.startY) / ROW_H));
  if (dest !== current.origRow && lanes[dest]) {
    const target = blocks.find(
      (other) => other.id !== block.id && other.pca === lanes[dest].pca && other.servo === lanes[dest].servo,
    );
    if (target) {
      const pca = block.pca;
      const servo = block.servo;
      block.pca = target.pca;
      block.servo = target.servo;
      target.pca = pca;
      target.servo = servo;
      block.nombre = `P${block.pca}_S${block.servo}`;
      target.nombre = `P${target.pca}_S${target.servo}`;
    }
  }
  render();
});

els.tracks.addEventListener("dblclick", (event) => {
  const node = event.target.closest(".block");
  if (!node) return;
  selectBlock(Number(node.dataset.id));
  document.getElementById("edit-nombre").focus();
});

["edit-nombre", "edit-pca", "edit-servo", "edit-pos", "edit-vel", "edit-dur"].forEach((id) => {
  document.getElementById(id).addEventListener("change", applyInspector);
});

document.getElementById("delete-block").onclick = deleteSelected;

document.getElementById("add").onclick = () => {
  const block = createBlock();
  blocks.push(block);
  selectedId = block.id;
  render();
};

document.getElementById("save").onclick = async () => {
  const sequence = buildOrigin();
  if (!sequence.name || !sequence.blocks.length) {
    setStatus("Define nombre y bloques", true);
    return;
  }
  try {
    const saved = isCoupled() ? await saveCoupled(false) : await saveLocal(false);
    if (!saved) return;
    selectedLibraryName = sequence.name;
    await refreshLibrary();
    setStatus(isCoupled() ? "Secuencia guardada en robótica" : "Secuencia guardada en disco");
  } catch (error) {
    setStatus(error.message || "No se pudo guardar", true);
  }
};

document.getElementById("play").onclick = () => playCurrent();

document.getElementById("stop").onclick = async () => {
  stopPlayhead();
  if (token && gatewayUrl) {
    try {
      await authorizedFetch("/sequence/stop", { method: "POST", body: "{}" });
    } catch {
      /* the playhead still stops locally */
    }
  }
  setStatus("Detenido");
};

document.getElementById("load").onclick = () => refreshLibrary();

els.stage.addEventListener("scroll", () => {
  els.lanes.scrollTop = els.stage.scrollTop;
});

drawRuler();
render();
refreshLibrary();
setStatus("Listo");
