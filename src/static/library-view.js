(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.StudioLibrary = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const NEUTRO_REVIEW_WARNING =
    "El neutro generado debe revisarlo una persona. En el androide no es fiable.";

  function formatArduinoStatus(list) {
    if (!list || !list.length) return { connected: false, label: "Sin Arduino" };
    if (list.length === 1) {
      return { connected: true, label: `Arduino #${list[0].arduino_id} · ${list[0].port}` };
    }
    return { connected: true, label: `${list.length} conectados` };
  }

  function blockCardText(block) {
    const parts = [
      block.nombre,
      `pca:${block.pca}`,
      `s:${block.servo}`,
      `t:${block.inicio}`,
      `d:${block.dur}`,
      `pos:${block.pos}`,
      `v:${block.vel}`,
    ];
    if (Number(block.arduino_id) !== 0) parts.push(`ard:${block.arduino_id}`);
    return parts.join(" ");
  }

  function groupLibraryItems(items) {
    const buckets = new Map();
    for (const item of items) {
      const key = item.category && String(item.category).trim() ? String(item.category) : "Sin categoría";
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(item);
    }
    const named = [...buckets.keys()].filter((key) => key !== "Sin categoría").sort();
    const order = named.concat(buckets.has("Sin categoría") ? ["Sin categoría"] : []);
    return order.map((label) => ({ label, items: buckets.get(label) }));
  }

  return { NEUTRO_REVIEW_WARNING, formatArduinoStatus, blockCardText, groupLibraryItems };
});
