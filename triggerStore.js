// TRIGGER-STORE-V1: in-memory mapping-store voor trigger-feature.
// Fase 2-skeleton: load uit cfg.triggers, beheer in geheugen.
// save-naar-disk komt later via existing session-save-flow.

let mappings = [];
let nextId = 1;

function load(cfg) {
  if (!Array.isArray(cfg.triggers)) {
    cfg.triggers = [];
  }
  mappings = cfg.triggers.map(m => ({ ...m }));
  // Bepaal volgende id op basis van bestaande ids
  for (const m of mappings) {
    if (typeof m.id === "number" && m.id >= nextId) nextId = m.id + 1;
  }
  console.log(`[trigger-store] loaded ${mappings.length} mapping(s)`);
}

function getAll() {
  return mappings.map(m => ({ ...m }));
}

function add(mapping) {
  const id = nextId++;
  const stored = { id, ...mapping };
  mappings.push(stored);
  console.log(`[trigger-store] added mapping id=${id} action=${mapping.action} protocol=${mapping.protocol}`);
  return stored;
}

function remove(id) {
  const idx = mappings.findIndex(m => m.id === id);
  if (idx === -1) return false;
  mappings.splice(idx, 1);
  console.log(`[trigger-store] removed mapping id=${id}`);
  return true;
}

// Match een normalized event tegen alle mappings.
// Returns array van matchende mappings (kan leeg zijn).
function matchEvent(evt) {
  return mappings.filter(m => {
    if (m.protocol !== evt.protocol) return false;
    return signaturesMatch(m.signature, evt.signature);
  });
}

function signaturesMatch(a, b) {
  // Voor elk veld in a moet b dezelfde waarde hebben.
  // a is de mapping-signature (kan minder velden hebben dan event-signature).
  for (const key of Object.keys(a)) {
    if (a[key] !== b[key]) return false;
  }
  return true;
}

module.exports = { load, getAll, add, remove, matchEvent };
