// TRIGGER-FEATURE-V1: MIDI listener voor pedaal/keyboard/Glover-input.
// Fase 1 minimaal: alleen detectie + logging naar terminal.

const easymidi = require("easymidi");

let inputs = [];

function start() {
  const deviceNames = easymidi.getInputs();
  console.log(`[trigger] MIDI: ${deviceNames.length} input devices: ${deviceNames.join(", ") || "(none)"}`);

  for (const name of deviceNames) {
    try {
      const input = new easymidi.Input(name);

      input.on("cc", (msg) => {
        console.log(`[trigger] MIDI cc  device="${name}" channel=${msg.channel} controller=${msg.controller} value=${msg.value}`);
      });
      input.on("noteon", (msg) => {
        console.log(`[trigger] MIDI on  device="${name}" channel=${msg.channel} note=${msg.note} velocity=${msg.velocity}`);
      });
      input.on("noteoff", (msg) => {
        console.log(`[trigger] MIDI off device="${name}" channel=${msg.channel} note=${msg.note} velocity=${msg.velocity}`);
      });

      inputs.push(input);
      console.log(`[trigger] listening on "${name}"`);
    } catch (err) {
      console.log(`[trigger] failed to open "${name}": ${err.message}`);
    }
  }
}

function stop() {
  for (const input of inputs) {
    try { input.close(); } catch (_) {}
  }
  inputs = [];
}

module.exports = { start, stop };
