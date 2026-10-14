const POST_AUTH = "prometeo-auth";
const POST_AUTH_REQUEST = "prometeo-auth-request";
let token = null;
let gatewayUrl = null;

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
  document.getElementById("mode").textContent = "Acoplado";
});

function addRow(values) {
  const [pca, servo, inicio, dur, pos, vel, nombre] = values || [0, 0, 0, 1, 0, 1, "P0_S0"];
  const row = document.createElement("tr");
  row.innerHTML = `
    <td><input class="pca" type="number" min="0" max="10" value="${pca}" /></td>
    <td><input class="servo" type="number" min="0" max="15" value="${servo}" /></td>
    <td><input class="inicio" type="number" min="0" step="0.01" value="${inicio}" /></td>
    <td><input class="dur" type="number" min="0.0001" step="0.01" value="${dur}" /></td>
    <td><input class="pos" type="number" min="0" max="1000" value="${pos}" /></td>
    <td><input class="vel" type="number" min="1" max="10" value="${vel}" /></td>
    <td><input class="nombre" maxlength="80" value="${nombre}" /></td>
  `;
  document.getElementById("blocks").appendChild(row);
}

function buildOrigin() {
  const name = document.getElementById("name").value.trim();
  const description = document.getElementById("description").value.replace(/\n/g, " ").slice(0, 280);
  const arduino_id = Number(document.getElementById("arduino_id").value || 0);
  const blocks = [...document.querySelectorAll("tbody tr")].map((row) => {
    const v = (cls) => row.querySelector(cls).value;
    return [
      Number(v(".pca")),
      Number(v(".servo")),
      Number(v(".inicio")),
      Number(v(".dur")),
      Number(v(".pos")),
      Number(v(".vel")),
      String(v(".nombre")),
    ];
  });
  return { name, description, arduino_id, blocks };
}

async function saveCoupled(overwrite) {
  const sequence = buildOrigin();
  const response = await fetch(`${gatewayUrl}/sequence/file`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ sequence, overwrite: Boolean(overwrite) }),
  });
  if (response.status === 401 || response.status === 403) {
    token = null;
    document.getElementById("mode").textContent = "Suelto: no hay sesión";
    window.parent.postMessage({ type: POST_AUTH_REQUEST }, "*");
    throw new Error("Sesión vencida");
  }
  if (!response.ok) {
    const text = await response.text();
    if (!overwrite && /ya existe/i.test(text)) {
      if (confirm("La secuencia ya existe. ¿Sobrescribir?")) {
        return saveCoupled(true);
      }
      return;
    }
    throw new Error("No se pudo guardar");
  }
}

document.getElementById("add-row").onclick = () => addRow();

document.getElementById("save").onclick = async () => {
  const sequence = buildOrigin();
  if (!sequence.name || !sequence.blocks.length) {
    document.getElementById("status").textContent = "Define nombre y bloques";
    return;
  }
  try {
    if (token && gatewayUrl) {
      await saveCoupled(false);
      document.getElementById("status").textContent = "Secuencia guardada";
      return;
    }
    const blob = new Blob([JSON.stringify(sequence, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${sequence.name}.json`;
    link.click();
    document.getElementById("status").textContent = "JSON descargado (suelto)";
  } catch (error) {
    document.getElementById("status").textContent = error.message || "No se pudo guardar";
  }
};

document.getElementById("play").onclick = async () => {
  const sequence = buildOrigin();
  if (!token || !gatewayUrl) {
    document.getElementById("status").textContent = "Suelto: no hay sesión";
    return;
  }
  if (!sequence.blocks.length) {
    document.getElementById("status").textContent = "Define nombre y bloques";
    return;
  }
  const blocks = sequence.blocks.map((item) => ({
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
    const response = await fetch(`${gatewayUrl}/sequence/play`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ blocks }),
    });
    if (!response.ok) {
      throw new Error("No se pudo previsualizar");
    }
    document.getElementById("status").textContent = "Previsualización enviada";
  } catch (error) {
    document.getElementById("status").textContent = error.message || "No se pudo previsualizar";
  }
};

addRow();
