// TRIGGER-FEATURE-V1: MIDI listener voor pedaal/keyboard/Glover-input.
// Fase 1 minimaal: alleen detectie + logging naar terminal.

const easymidi = require("easymidi");
const { Server: OscServer } = require("node-osc"); // TRIGGER-OSC-V1

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

  // TRIGGER-OSC-V1: OSC listener op UDP 9100
  try {
    const oscPort = 9100;
    const oscServer = new OscServer(oscPort, "0.0.0.0", () => {
      console.log(`[trigger] OSC: listening on UDP port ${oscPort}`);
    });
    oscServer.on("message", (msg, rinfo) => {
      const remoteAddr = rinfo ? `${rinfo.address}:${rinfo.port}` : "unknown";
      console.log(`[trigger] OSC msg src=${remoteAddr} path=${msg[0]} args=${JSON.stringify(msg.slice(1))}`);
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
}

module.exports = { start, stop };
