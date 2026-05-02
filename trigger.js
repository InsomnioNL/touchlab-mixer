// TRIGGER-FEATURE-V1: input listeners voor pedaal/keyboard/Glover/etc.
// TRIGGER-NORMALIZE-V1: alle protocollen normaliseren naar interne event-vorm,
// gemeenschappelijke onEvent() doet mapping-match en logging.

const easymidi = require("easymidi");
const { Server: OscServer } = require("node-osc"); // TRIGGER-OSC-V1
const triggerStore = require("./triggerStore");

let inputs = [];
let oscServer = null;

// TRIGGER-NORMALIZE-V1: centrale event-handler.
// Alle protocol-listeners normaliseren naar deze vorm en roepen onEvent aan.
// Interne event-vorm:
//   { protocol, source, signature, value, timestamp }
function onEvent(evt) {
  const matches = triggerStore.matchEvent(evt);
  const sigStr = JSON.stringify(evt.signature);
  if (matches.length === 0) {
    console.log(`[trigger] EVENT [${evt.protocol}] src=${evt.source} sig=${sigStr} val=${evt.value}`);
    return;
  }
  // TRIGGER-HYSTERESE-V1: per match hysterese-state evaluatie.
  // Binary bronnen (keyboard, of mapping zonder thresholds) → directe state-mapping.
  // Continuous bronnen (MIDI CC, OSC float) → vergelijk tegen mapping.thresholdActive/Inactive.
  for (const m of matches) {
    const transition = evaluateHysteresis(m, evt.value);
    if (transition === "no-change") {
      console.log(`[trigger] EVENT [${evt.protocol}] src=${evt.source} sig=${sigStr} val=${evt.value} → MATCH id=${m.id} action=${m.action} (no state change)`);
    } else {
      triggerStore.setState(m.id, transition === "activate" ? "ACTIVE" : "INACTIVE");
      console.log(`[trigger] EVENT [${evt.protocol}] src=${evt.source} sig=${sigStr} val=${evt.value} → MATCH id=${m.id} action=${m.action} TRANSITION=${transition.toUpperCase()}`);
    }
  }
}

// TRIGGER-HYSTERESE-V1: bepaal of een event een state-transitie veroorzaakt.
// Returns: "activate" | "release" | "no-change"
function evaluateHysteresis(mapping, value) {
  const currentState = triggerStore.getState(mapping.id);
  const hasThresholds = (mapping.thresholdActive !== undefined && mapping.thresholdInactive !== undefined);

  if (!hasThresholds) {
    // Binary mode: value 0 = inactive, value > 0 = active
    const wantActive = value > 0;
    if (wantActive && currentState === "INACTIVE") return "activate";
    if (!wantActive && currentState === "ACTIVE") return "release";
    return "no-change";
  }

  // Hysteresis mode
  if (currentState === "INACTIVE" && value >= mapping.thresholdActive) return "activate";
  if (currentState === "ACTIVE" && value <= mapping.thresholdInactive) return "release";
  return "no-change";
}

// MIDI normalize-helpers
function normalizeMidiCc(deviceName, msg) {
  return {
    protocol: "midi",
    source: deviceName,
    signature: { type: "cc", channel: msg.channel, number: msg.controller },
    value: msg.value,
    timestamp: Date.now()
  };
}

function normalizeMidiNote(deviceName, msg, isOn) {
  return {
    protocol: "midi",
    source: deviceName,
    signature: { type: "note", channel: msg.channel, note: msg.note },
    value: isOn ? msg.velocity : 0,
    timestamp: Date.now()
  };
}

// OSC normalize-helper
function normalizeOsc(remoteAddr, msg) {
  const path = msg[0];
  const args = msg.slice(1);
  return {
    protocol: "osc",
    source: remoteAddr,
    signature: { path },
    value: typeof args[0] === "number" ? args[0] : 0,
    timestamp: Date.now()
  };
}

// Keyboard normalize-helper (aangeroepen vanuit bridge.js bij keyboard-event WS-message)
function normalizeKeyboard(uiPayload) {
  return {
    protocol: "keyboard",
    source: "ui",
    signature: { key: uiPayload.key },
    value: uiPayload.value,
    timestamp: uiPayload.timestamp || Date.now()
  };
}

// Externe entry-point voor bridge.js om keyboard-events door te leiden
function handleKeyboardEvent(uiPayload) {
  if (typeof uiPayload.key !== "string") return;
  if (uiPayload.value !== 0 && uiPayload.value !== 1) return;
  onEvent(normalizeKeyboard(uiPayload));
}

function start() {
  const deviceNames = easymidi.getInputs();
  console.log(`[trigger] MIDI: ${deviceNames.length} input devices: ${deviceNames.join(", ") || "(none)"}`);
  for (const name of deviceNames) {
    try {
      const input = new easymidi.Input(name);
      input.on("cc", (msg) => onEvent(normalizeMidiCc(name, msg)));
      input.on("noteon", (msg) => onEvent(normalizeMidiNote(name, msg, true)));
      input.on("noteoff", (msg) => onEvent(normalizeMidiNote(name, msg, false)));
      inputs.push(input);
      console.log(`[trigger] listening on "${name}"`);
    } catch (err) {
      console.log(`[trigger] failed to open "${name}": ${err.message}`);
    }
  }

  // TRIGGER-OSC-V1: OSC listener op UDP 9100
  try {
    const oscPort = 9100;
    oscServer = new OscServer(oscPort, "0.0.0.0", () => {
      console.log(`[trigger] OSC: listening on UDP port ${oscPort}`);
    });
    oscServer.on("message", (msg, rinfo) => {
      const remoteAddr = rinfo ? `${rinfo.address}:${rinfo.port}` : "unknown";
      onEvent(normalizeOsc(remoteAddr, msg));
    });
    oscServer.on("error", (err) => {
      console.log(`[trigger] OSC error: ${err.message}`);
    });
  } catch (err) {
    console.log(`[trigger] OSC failed to start: ${err.message}`);
  }
}

function stop() {
  for (const input of inputs) {
    try { input.close(); } catch (_) {}
  }
  inputs = [];
  if (oscServer) {
    try { oscServer.close(); } catch (_) {}
    oscServer = null;
  }
}

module.exports = { start, stop, handleKeyboardEvent };
