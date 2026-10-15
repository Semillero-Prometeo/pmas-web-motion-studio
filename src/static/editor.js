const POST_AUTH = "prometeo-auth";
const POST_AUTH_REQUEST = "prometeo-auth-request";
const PX = 100;
const ROW_H = 44;
const SECONDS = 41;
const COLORS = ["#38bdf8", "#7dd3fc", "#0ea5e9", "#67e8f9", "#22d3ee"];
const COLORS_OVERLAP = ["#0284c7", "#0369a1", "#155e75", "#0e7490", "#164e63"];
const COLORS_NEUTRO = ["#059669", "#047857", "#065f46", "#34d399", "#6ee7b7"];
const COLORS_NEUTRO_OVERLAP = ["#047857", "#065f46", "#064e3b", "#059669", "#047857"];

let token = null;
let gatewayUrl = null;
let activeRole = null;
let lastAuthKey = null;
let authRequestAt = 0;
let gestureBlocks = [];
let neutroBlocks = [];
let activeTrack = "normal";
let blocks = gestureBlocks;
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
  category: document.getElementById("category"),
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
  const role = typeof data.activeRole === "string" ? data.activeRole.trim() : "";
  const nextKey = `${data.token}|${role}|${data.gatewayUrl}`;
  if (nextKey === lastAuthKey) return;
  lastAuthKey = nextKey;
  token = data.token;
  gatewayUrl = data.gatewayUrl.replace(/\/$/, "");
  activeRole = role || null;
  if (!activeRole) {
    els.mode.textContent = "Suelto";
    setStatus("Falta el rol activo; se usa el disco local", true);
    refreshLibrary();
    return;
  }
  els.mode.textContent = "Acoplado";
  setStatus("Acoplado a robótica");
  refreshLibrary();
});

function isCoupled() {
  return Boolean(token && gatewayUrl && activeRole);
}

function requestAuth() {
  const now = Date.now();
  if (now - authRequestAt < 2000) return;
  authRequestAt = now;
  window.parent.postMessage({ type: POST_AUTH_REQUEST }, "*");
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
        const palette = activeTrack === "neutro" ? COLORS_NEUTRO : COLORS;
        const overlapPalette = activeTrack === "neutro" ? COLORS_NEUTRO_OVERLAP : COLORS_OVERLAP;
        el.style.background = overlapping
          ? overlapPalette[(row + order) % overlapPalette.length]
          : palette[(row + order) % palette.length];
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

function tuplesOf(list) {
  return list.map((block) => [
    Number(block.pca),
    Number(block.servo),
    roundTime(block.inicio),
    Number(block.dur),
    Number(block.pos),
    Number(block.vel),
    String(block.nombre),
  ]);
}

function flushActive() {
  if (activeTrack === "neutro") {
    neutroBlocks = blocks;
  } else {
    gestureBlocks = blocks;
  }
}

function setActiveTrack(next) {
  flushActive();
  activeTrack = next;
  blocks = next === "neutro" ? neutroBlocks : gestureBlocks;
  document.getElementById("track-gesto").classList.toggle("active", next === "normal");
  document.getElementById("track-neutro").classList.toggle("active", next === "neutro");
  document.documentElement.classList.toggle("track-neutro", next === "neutro");
  selectedId = null;
  render();
}

function generateNeutroFrom(tuples) {
  if (!tuples.length) return [];
  const ordered = tuples.map((item, index) => ({ item, index }));
  ordered.sort((a, b) => {
    const start = Number(a.item[2]) - Number(b.item[2]);
    return start !== 0 ? start : a.index - b.index;
  });
  const prev = new Map();
  const undos = [];
  for (const { item, index } of ordered) {
    const key = `${item[0]}:${item[1]}`;
    const inicio = Number(item[2]);
    const dur = Number(item[3]);
    undos.push({
      index,
      row: [item[0], item[1], inicio, dur, prev.has(key) ? prev.get(key) : 0, item[5], item[6]],
    });
    prev.set(key, item[4]);
  }
  const tEnd = Math.max(...tuples.map((item) => Number(item[2]) + Number(item[3])));
  return undos
    .map(({ index, row }) => {
      const inicio = Number(row[2]);
      const dur = Number(row[3]);
      row[2] = tEnd - (inicio + dur);
      return { index, row };
    })
    .sort((a, b) => {
      const start = Number(a.row[2]) - Number(b.row[2]);
      return start !== 0 ? start : b.index - a.index;
    })
    .map(({ row }) => row);
}

function generateNeutro() {
  flushActive();
  if (!gestureBlocks.length) {
    setStatus("Agrega bloques al gesto", true);
    return;
  }
  if (neutroBlocks.length && !confirm("¿Reemplazar la pista neutra?")) return;
  neutroBlocks = generateNeutroFrom(tuplesOf(gestureBlocks)).map((item) =>
    createBlock({
      pca: item[0],
      servo: item[1],
      inicio: item[2],
      dur: item[3],
      pos: item[4],
      vel: item[5],
      nombre: item[6],
    }),
  );
  if (activeTrack === "neutro") blocks = neutroBlocks;
  render();
  setStatus("Pista neutra generada");
}

function setSaveError(message) {
  const node = document.getElementById("save-error");
  if (!message) {
    node.hidden = true;
    node.textContent = "";
    return;
  }
  node.hidden = false;
  node.textContent = message;
}

function openSaveDialog() {
  setSaveError("");
  document.getElementById("save-dialog").showModal();
}

async function confirmSave(event) {
  event.preventDefault();
  const sequence = buildOrigin();
  const description = sequence.description.trim();
  if (!sequence.name) {
    setSaveError("Escribe un nombre.");
    return;
  }
  if (description.length < 10) {
    setSaveError("La descripción debe tener al menos 10 caracteres.");
    return;
  }
  if (!sequence.category) {
    setSaveError("Elige una categoría.");
    return;
  }
  if (!sequence.blocks.length || !sequence.blocks_neutro.length) {
    setSaveError("Categoría, gesto y neutro son obligatorios");
    return;
  }
  try {
    const saved = isCoupled() ? await saveCoupled(false) : await saveLocal(false);
    if (!saved) return;
    selectedLibraryName = sequence.name;
    document.getElementById("save-dialog").close();
    await refreshLibrary();
    setStatus(isCoupled() ? "Secuencia guardada en robótica" : "Secuencia guardada en disco");
  } catch (error) {
    setSaveError(error.message || "No se pudo guardar");
    setStatus(error.message || "No se pudo guardar", true);
  }
}

function buildOrigin() {
  flushActive();
  return {
    name: els.name.value.trim(),
    description: els.description.value.replace(/\n/g, " ").slice(0, 280),
    category: els.category.value,
    arduino_id: Number(els.arduino.value || 0),
    blocks: tuplesOf(gestureBlocks),
    blocks_neutro: tuplesOf(neutroBlocks),
  };
}

async function authorizedFetch(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
    ...(options.headers || {}),
  };
  if (activeRole) headers["X-Active-Role"] = activeRole;
  const response = await fetch(`${gatewayUrl}${path}`, {
    ...options,
    headers,
  });
  if (response.status === 401) {
    token = null;
    activeRole = null;
    els.mode.textContent = "Suelto: no hay sesión";
    requestAuth();
    throw new Error("Sesión vencida");
  }
  return response;
}

async function readError(response) {
  const text = await response.text();
  try {
    const json = JSON.parse(text);
    if (typeof json.detail === "string") return json.detail;
    if (typeof json.message === "string") return json.message;
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
  if (isCoupled()) {
    try {
      const response = await authorizedFetch("/sequence/files");
      if (!response.ok) throw new Error((await readError(response)) || "No se pudo listar");
      libraryItems = (await response.json()).data || [];
      renderLibrary();
      return;
    } catch (error) {
      setStatus(error.message || "No se pudo listar", true);
      if (isCoupled()) {
        libraryItems = [];
        renderLibrary();
        return;
      }
    }
  }
  try {
    const response = await fetch("/local/sequences");
    if (!response.ok) throw new Error("No se pudo listar el disco");
    libraryItems = (await response.json()).data || [];
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
  flushActive();
  const active = activeTrack === "neutro" ? neutroBlocks : gestureBlocks;
  if (!active.length) {
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
  const sequence = buildOrigin();
  const playBlocks = tuplesOf(active).map((item) => ({
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
      body: JSON.stringify({
        mode: activeTrack === "neutro" ? "neutro" : "normal",
        source: "estudio",
        blocks: playBlocks,
      }),
    });
    if (!response.ok) {
      stopPlayhead();
      setStatus((await readError(response)) || "No se pudo previsualizar", true);
      return;
    }
    setStatus("Previsualización en curso");
  } catch (error) {
    stopPlayhead();
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

function mapRawBlocks(rawBlocks) {
  return rawBlocks.map((item) => {
    if (Array.isArray(item)) {
      return createBlock({
        pca: item[0],
        servo: item[1],
        inicio: item[2],
        dur: item[3],
        pos: item[4],
        vel: item[5],
        nombre: item[6],
      });
    }
    return createBlock({
      pca: item.pca,
      servo: item.servo,
      inicio: item.inicio,
      dur: item.dur,
      pos: item.pos,
      vel: item.vel,
      nombre: item.nombre,
    });
  });
}

function parseLoadedSequence(payload) {
  const sequence = payload.sequence || payload;
  els.name.value = sequence.name || "";
  els.description.value = sequence.description || "";
  els.category.value = sequence.category || "";
  const rawBlocks = Array.isArray(sequence.blocks) ? sequence.blocks : [];
  const rawNeutro = Array.isArray(sequence.blocks_neutro) ? sequence.blocks_neutro : [];
  if (sequence.arduino_id != null) {
    els.arduino.value = sequence.arduino_id;
  } else if (rawBlocks[0] && !Array.isArray(rawBlocks[0]) && rawBlocks[0].arduino_id != null) {
    els.arduino.value = rawBlocks[0].arduino_id;
  }
  gestureBlocks = mapRawBlocks(rawBlocks);
  neutroBlocks = mapRawBlocks(rawNeutro);
  activeTrack = "normal";
  blocks = gestureBlocks;
  document.getElementById("track-gesto").classList.add("active");
  document.getElementById("track-neutro").classList.remove("active");
  document.documentElement.classList.remove("track-neutro");
  selectedId = null;
  render();
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

document.getElementById("track-gesto").onclick = () => setActiveTrack("normal");
document.getElementById("track-neutro").onclick = () => setActiveTrack("neutro");
document.getElementById("generate-neutro").onclick = () => generateNeutro();

document.getElementById("save").onclick = () => openSaveDialog();
document.getElementById("save-form").addEventListener("submit", (event) => {
  void confirmSave(event);
});
document.getElementById("save-cancel").onclick = () => {
  document.getElementById("save-dialog").close();
};
document.getElementById("save-dialog").addEventListener("cancel", () => setSaveError(""));

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
