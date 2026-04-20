/**
 * TouchLab Mixer Bridge
 * 
 * Verbindt de frontend (WebSocket) met Pure Data (UDP/FUDI).
 * Handelt mute + solo logica af (zodat PD alleen een simpele gate waarde krijgt).
 * Stuurt VU meter data terug naar de frontend.
 * 
 * Installatie:
 *   npm install ws osc
 * 
 * Start:
 *   node bridge.js [session.json]
 */

const dgram   = require("dgram");
const net     = require("net");
const fs      = require("fs");
const path    = require("path");
const { WebSocketServer } = require("ws");

// ─── Config laden ──────────────────────────────────────────────────────────
const configPath = process.argv[2] || "session.json";
const cfg        = JSON.parse(fs.readFileSync(configPath, "utf8"));

const PD_FUDI_PORT  = cfg.osc_receive_port  || 9000;  // bridge → PD (TCP FUDI)
const VU_LISTEN_PORT = cfg.vu_send_port      || 9001;  // PD → bridge (UDP)
const WS_PORT       = cfg.ws_port            || 8080;  // frontend ↔ bridge (WebSocket)
const CHANNELS      = cfg.channels;
const N             = CHANNELS.length;

// ─── State ─────────────────────────────────────────────────────────────────
const state = {};
CHANNELS.forEach(ch => {
  state[ch.index] = {
    name:  ch.name,
    vol:   0.8,
    pan:   0.5,
    mute:  false,
    solo:  false,
    fx:    0.0,
    vu:    -100,
  };
});
let masterVol = 0.8;
let hpVol     = 0.8;
let fxReturn  = 0.0;
let masterVu  = -100;

// ─── Solo gate berekening ───────────────────────────────────────────────────
function soloCount() {
  return CHANNELS.filter(ch => state[ch.index].solo).length;
}

function computeGate(chIdx) {
  const s    = state[chIdx];
  const nSolo = soloCount();
  if (s.mute) return 0;
  if (nSolo === 0) return 1;
  return s.solo ? 1 : 0;
}

// ─── PD FUDI verbinding (TCP) ───────────────────────────────────────────────
// PD draait netreceive op PD_FUDI_PORT in TCP modus.
// Wij verbinden als client en sturen FUDI berichten.
let pdSocket = null;
let pdReady  = false;

function connectToPD() {
  pdSocket = net.connect(PD_FUDI_PORT, "127.0.0.1", () => {
    pdReady = true;
    console.log(`✓  Verbonden met PD op poort ${PD_FUDI_PORT}`);
    initPD();
  });
  pdSocket.on("error", err => {
    pdReady = false;
    console.warn(`⚠  PD niet bereikbaar (${err.message}), opnieuw proberen in 3s...`);
    setTimeout(connectToPD, 3000);
  });
  pdSocket.on("close", () => {
    pdReady = false;
    console.warn("⚠  PD verbinding verbroken, opnieuw verbinden...");
    setTimeout(connectToPD, 3000);
  });
}

function sendPD(receiver, ...args) {
  if (!pdReady || !pdSocket) return;
  // FUDI formaat: ;receiver arg1 arg2;
  const msg = `; ${receiver} ${args.join(" ")};\n`;
  pdSocket.write(msg);
}

function initPD() {
  // Stuur beginwaarden voor alle kanalen
  CHANNELS.forEach(ch => {
    const s = state[ch.index];
    sendPD(`ch${ch.index}-vol`,  s.vol);
    sendPD(`ch${ch.index}-pan`,  s.pan);
    sendPD(`ch${ch.index}-gate`, computeGate(ch.index));
    sendPD(`ch${ch.index}-fx`,   s.fx);
  });
  sendPD("masterVol", masterVol);
  sendPD("hpVol",     hpVol);
  sendPD("fxReturn",  fxReturn);
  console.log("✓  Beginwaarden naar PD gestuurd");
}

// ─── VU ontvangst van PD (UDP) ─────────────────────────────────────────────
const vuServer = dgram.createSocket("udp4");
vuServer.bind(VU_LISTEN_PORT, () => {
  console.log(`✓  VU luisteren op UDP ${VU_LISTEN_PORT}`);
});

vuServer.on("message", buf => {
  // Formaat van PD: "vu 1 -23.5;\n" of "vu master -20.0;\n"
  const text = buf.toString().replace(/;\s*$/, "").trim();
  const parts = text.split(/\s+/);
  if (parts[0] !== "vu" || parts.length < 3) return;

  const who = parts[1];
  const val = parseFloat(parts[2]);

  if (who === "master") {
    masterVu = val;
  } else {
    const idx = parseInt(who);
    if (state[idx]) state[idx].vu = val;
  }

  // Doorsturen naar alle WebSocket clients
  broadcastVU();
});

// ─── WebSocket server (frontend) ───────────────────────────────────────────
const wss = new WebSocketServer({ port: WS_PORT });
const wsClients = new Set();

wss.on("listening", () => {
  console.log(`✓  WebSocket server op ws://localhost:${WS_PORT}`);
});

wss.on("connection", ws => {
  wsClients.add(ws);
  console.log(`+  Frontend verbonden (${wsClients.size} clients)`);

  // Stuur volledige huidige staat bij verbinding
  ws.send(JSON.stringify({
    type:     "init",
    channels: CHANNELS.map(ch => ({
      index: ch.index,
      name:  ch.name,
      vol:   state[ch.index].vol,
      pan:   state[ch.index].pan,
      mute:  state[ch.index].mute,
      solo:  state[ch.index].solo,
      fx:    state[ch.index].fx,
    })),
    master: { vol: masterVol, hp: hpVol, fxReturn },
  }));

  ws.on("message", raw => {
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }
    handleFrontendMessage(msg);
  });

  ws.on("close", () => {
    wsClients.delete(ws);
    console.log(`-  Frontend verbroken (${wsClients.size} clients)`);
  });
});

function broadcast(obj) {
  const data = JSON.stringify(obj);
  wsClients.forEach(ws => {
    if (ws.readyState === 1) ws.send(data);
  });
}

function broadcastVU() {
  broadcast({
    type: "vu",
    channels: CHANNELS.map(ch => ({
      index: ch.index,
      vu:    state[ch.index].vu,
    })),
    masterVu,
  });
}

// ─── Frontend berichten verwerken ──────────────────────────────────────────
function handleFrontendMessage(msg) {
  const { type, channel, value } = msg;

  switch (type) {

    case "volume": {
      const v = clamp(value, 0, 1);
      state[channel].vol = v;
      sendPD(`ch${channel}-vol`, v);
      broadcast({ type: "volume", channel, value: v });
      break;
    }

    case "pan": {
      const v = clamp(value, 0, 1);
      state[channel].pan = v;
      sendPD(`ch${channel}-pan`, v);
      broadcast({ type: "pan", channel, value: v });
      break;
    }

    case "mute": {
      state[channel].mute = !!value;
      // Herbereken alle gates (solo kan gewijzigd zijn door mute)
      updateAllGates();
      broadcast({ type: "mute", channel, value: state[channel].mute });
      break;
    }

    case "solo": {
      state[channel].solo = !!value;
      // Solo verandert de gate van ALLE kanalen
      updateAllGates();
      broadcast({ type: "solo", channel, value: state[channel].solo });
      break;
    }

    case "fx": {
      const v = clamp(value, 0, 1);
      state[channel].fx = v;
      sendPD(`ch${channel}-fx`, v);
      broadcast({ type: "fx", channel, value: v });
      break;
    }

    case "masterVol": {
      masterVol = clamp(value, 0, 1);
      sendPD("masterVol", masterVol);
      broadcast({ type: "masterVol", value: masterVol });
      break;
    }

    case "hpVol": {
      hpVol = clamp(value, 0, 1);
      sendPD("hpVol", hpVol);
      broadcast({ type: "hpVol", value: hpVol });
      break;
    }

    case "fxReturn": {
      fxReturn = clamp(value, 0, 1);
      sendPD("fxReturn", fxReturn);
      broadcast({ type: "fxReturn", value: fxReturn });
      break;
    }

    default:
      console.warn("Onbekend bericht type:", type);
  }
}

function updateAllGates() {
  CHANNELS.forEach(ch => {
    const gate = computeGate(ch.index);
    sendPD(`ch${ch.index}-gate`, gate);
  });
}

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

// ─── Start ─────────────────────────────────────────────────────────────────
console.log("TouchLab Mixer Bridge");
console.log(`Config: ${configPath} (${N} kanalen)`);
console.log("─".repeat(40));
connectToPD();
