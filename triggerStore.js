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
  const withDefaults = applyThresholdDefaults(mapping); // TRIGGER-HYSTERESE-V1
  const stored = { id, ...withDefaults };
  mappings.push(stored);
  console.log(`[trigger-store] added mapping id=${id} action=${mapping.action} protocol=${mapping.protocol}`);
  return stored;
}

// TRIGGER-HYSTERESE-V1: sane default thresholds per protocol als ze niet meegegeven zijn.
// Continuous bronnen krijgen actieve/inactieve thresholds.
// Binary bronnen (keyboard) krijgen geen — hysterese wordt overgeslagen in trigger.js.
function applyThresholdDefaults(m) {
  if (m.thresholdActive !== undefined && m.thresholdInactive !== undefined) return m;
  const p = m.protocol;
  if (p === "midi") {
    return { thresholdActive: 64, thresholdInactive: 32, ...m };
  }
  if (p === "osc") {
    return { thresholdActive: 0.5, thresholdInactive: 0.3, ...m };
  }
  // keyboard or unknown: no thresholds
  return m;
}

function remove(id) {
  const idx = mappings.findIndex(m => m.id === id);
  if (idx === -1) return false;
  mappings.splice(idx, 1);
  stateById.delete(id); // TRIGGER-HYSTERESE-V1
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

// TRIGGER-HYSTERESE-V1: runtime state per mapping (niet gepersisteerd).
// Gebruikt door trigger.js voor hysterese-state-machine.
const stateById = new Map(); // id -> "ACTIVE" | "INACTIVE"

function getState(id) {
  return stateById.get(id) || "INACTIVE";
}

function setState(id, state) {
  stateById.set(id, state);
}

function clearStateForRemoved(id) {
  stateById.delete(id);
}

module.exports = { load, getAll, add, remove, matchEvent, getState, setState, clearStateForRemoved };
