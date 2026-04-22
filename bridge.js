/**
 * TouchLab Mixer Bridge — met opname functie
 */

const dgram   = require("dgram");
const net     = require("net");
const fs      = require("fs");
const path    = require("path");
const http    = require("http");
const { spawn, execSync } = require("child_process");
const { WebSocketServer } = require("ws");

// ─── Config laden ──────────────────────────────────────────────────────────
const configPath = process.argv[2] || "session.json";
const cfg        = JSON.parse(fs.readFileSync(configPath, "utf8"));

const sessionName    = cfg.session_name || cfg.session || path.basename(configPath, ".json");
const PD_FUDI_PORT   = cfg.osc_receive_port || 9000;
const VU_LISTEN_PORT = cfg.vu_send_port     || 9001;
const WS_PORT        = cfg.ws_port          || 8080;
const CHANNELS       = cfg.channels;
const N              = CHANNELS.length;
const REC_DIR        = cfg.recordings_path  || path.join(process.env.HOME, "recordings");
const TIMEMACHINE    = cfg.recording && cfg.recording.prebuffer ? cfg.recording.prebuffer : 0;

// Zorg dat recordings map bestaat
if (!fs.existsSync(REC_DIR)) fs.mkdirSync(REC_DIR, { recursive: true });

// ─── State ─────────────────────────────────────────────────────────────────
const state = {};
CHANNELS.forEach(ch => {
  state[ch.index] = { name: ch.name, vol: 0.8, pan: 0.5, mute: false, solo: false, fx: 0.0, vu: -100 };
});
let masterVol = 0.8, hpVol = 0.8, fxReturn = 0.0, masterVu = -100;

// ─── Opname state ──────────────────────────────────────────────────────────
let recProcess = null;
let recFile    = null;

function startRecording() {
  if (recProcess) return;
  const ts = new Date().toISOString().replace(/[:.]/g,"-").slice(0,19);
  const filename = `${sessionName}_${ts}.wav`;
  recFile = filename;
  const filepath = path.join(REC_DIR, filename);

  const args = ["--port", "system:playback_1", "--port", "system:playback_2", filepath];
  if (TIMEMACHINE > 0) {
    args.unshift("--timemachine", "--timemachine-prebuffer", String(TIMEMACHINE), "--maxbufsize", String(TIMEMACHINE + 60));
  }

  console.log(`⏺  Opname starten: ${filename}`);
  recProcess = spawn("jack_capture", args);
  recProcess.on("error", err => { console.warn("jack_capture fout:", err.message); recProcess = null; });
  recProcess.on("close", code => {
    console.log(`⏹  Opname gestopt (${recFile})`);
    broadcast({ type: "recStatus", recording: false, file: recFile });
    recProcess = null;
  });

  broadcast({ type: "recStatus", recording: true, file: null });
}

function stopRecording() {
  if (!recProcess) return;
  recProcess.stdin.write("\n"); // jack_capture stopt bij Enter
  setTimeout(() => { if (recProcess) recProcess.kill("SIGINT"); }, 500);
}

// ─── HTTP server voor downloads ────────────────────────────────────────────
const httpServer = http.createServer((req, res) => {
  const url = req.url;

  // CORS headers
  res.setHeader("Access-Control-Allow-Origin", "*");

  if (url === "/recordings" || url === "/recordings/") {
    // Lijst van opnames
    const files = fs.readdirSync(REC_DIR).filter(f => f.endsWith(".wav")).sort().reverse();
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>Opnames — ${sessionName}</title>
<style>body{font-family:monospace;background:#0a0018;color:#ccc;padding:20px}
h2{color:#b06af5}a{color:#45e68f;display:block;padding:8px 0;font-size:14px;border-bottom:1px solid #222}
</style></head><body>
<h2>${sessionName}</h2>
${files.map(f => `<a href="/recordings/${f}" download="${f}">⬇ ${f}</a>`).join("\n")}
${files.length === 0 ? "<p>Geen opnames</p>" : ""}
</body></html>`;
    res.writeHead(200, { "Content-Type": "text/html" });
    res.end(html);
    return;
  }

  if (url.startsWith("/recordings/")) {
    const filename = decodeURIComponent(url.slice(13));
    const filepath = path.join(REC_DIR, path.basename(filename));
    if (fs.existsSync(filepath)) {
      res.writeHead(200, {
        "Content-Type": "audio/wav",
        "Content-Disposition": `attachment; filename="${path.basename(filepath)}"`,
        "Content-Length": fs.statSync(filepath).size
      });
      fs.createReadStream(filepath).pipe(res);
    } else {
      res.writeHead(404); res.end("Niet gevonden");
    }
    return;
  }

  res.writeHead(404); res.end();
});

// ─── Solo gate ─────────────────────────────────────────────────────────────
function soloCount() { return CHANNELS.filter(ch => state[ch.index].solo).length; }
function computeGate(chIdx) {
  const s = state[chIdx], nSolo = soloCount();
  if (s.mute) return 0;
  if (nSolo === 0) return 1;
  return s.solo ? 1 : 0;
}

// ─── PD FUDI ───────────────────────────────────────────────────────────────
let pdSocket = null, pdReady = false;

function connectToPD() {
  pdSocket = net.connect(PD_FUDI_PORT, "127.0.0.1", () => {
    pdReady = true;
    console.log(`✓  Verbonden met PD op poort ${PD_FUDI_PORT}`);
    initPD();
  });
  pdSocket.on("error", err => { pdReady = false; console.warn(`⚠  PD: ${err.message}`); setTimeout(connectToPD, 3000); });
  pdSocket.on("close", () => { pdReady = false; setTimeout(connectToPD, 3000); });
}

function sendPD(receiver, ...args) {
  if (!pdReady || !pdSocket) return;
  pdSocket.write(`; ${receiver} ${args.join(" ")};\n`);
}

function initPD() {
  CHANNELS.forEach(ch => {
    const s = state[ch.index];
    sendPD(`ch${ch.index}-vol`, s.vol);
    sendPD(`ch${ch.index}-pan`, s.pan);
    sendPD(`ch${ch.index}-gate`, computeGate(ch.index));
    sendPD(`ch${ch.index}-fx`, s.fx);
  });
  sendPD("masterVol", masterVol);
  sendPD("hpVol", hpVol);
  sendPD("fxReturn", fxReturn);
  console.log("✓  Beginwaarden naar PD gestuurd");
}

// ─── VU ────────────────────────────────────────────────────────────────────
const vuServer = dgram.createSocket("udp4");
vuServer.bind(VU_LISTEN_PORT, () => console.log(`✓  VU luisteren op UDP ${VU_LISTEN_PORT}`));
vuServer.on("message", buf => {
  const parts = buf.toString().replace(/;\s*$/, "").trim().split(/\s+/);
  if (parts[0] !== "vu" || parts.length < 3) return;
  const who = parts[1], val = parseFloat(parts[2]);
  if (who === "master") masterVu = val;
  else { const idx = parseInt(who); if (state[idx]) state[idx].vu = val; }
  broadcastVU();
});

// ─── WebSocket ─────────────────────────────────────────────────────────────
const wss = new WebSocketServer({ server: httpServer });
const wsClients = new Set();

wss.on("connection", ws => {
  wsClients.add(ws);
  console.log(`+  Frontend verbonden (${wsClients.size} clients)`);
  ws.send(JSON.stringify({
    type: "init", session: sessionName,
    channels: CHANNELS.map(ch => ({
      index: ch.index, name: ch.name,
      vol: state[ch.index].vol, pan: state[ch.index].pan,
      mute: state[ch.index].mute, solo: state[ch.index].solo, fx: state[ch.index].fx,
    })),
    master: { vol: masterVol, hp: hpVol, fxReturn },
    ttb: cfg.ttb || null,
  }));
  ws.on("message", raw => { try { handleFrontendMessage(JSON.parse(raw)); } catch {} });
  ws.on("close", () => { wsClients.delete(ws); console.log(`-  Frontend verbroken (${wsClients.size} clients)`); });
});

function broadcast(obj) {
  const data = JSON.stringify(obj);
  wsClients.forEach(ws => { if (ws.readyState === 1) ws.send(data); });
}

function broadcastVU() {
  broadcast({ type: "vu", channels: CHANNELS.map(ch => ({ index: ch.index, vu: state[ch.index].vu })), masterVu });
}

// ─── Frontend berichten ─────────────────────────────────────────────────────
function handleFrontendMessage(msg) {
  const { type, channel, value } = msg;
  switch (type) {
    case "volume": { const v = clamp(value,0,1); state[channel].vol=v; sendPD(`ch${channel}-vol`,v); broadcast({type:"volume",channel,value:v}); break; }
    case "pan":    { const v = clamp(value,0,1); state[channel].pan=v; sendPD(`ch${channel}-pan`,v); broadcast({type:"pan",channel,value:v}); break; }
    case "mute":   { state[channel].mute=!!value; updateAllGates(); broadcast({type:"mute",channel,value:state[channel].mute}); break; }
    case "solo":   { state[channel].solo=!!value; updateAllGates(); broadcast({type:"solo",channel,value:state[channel].solo}); break; }
    case "fx":     { const v = clamp(value,0,1); state[channel].fx=v; sendPD(`ch${channel}-fx`,v); broadcast({type:"fx",channel,value:v}); break; }
    case "masterVol": { masterVol=clamp(value,0,1); sendPD("masterVol",masterVol); broadcast({type:"masterVol",value:masterVol}); break; }
    case "hpVol":     { hpVol=clamp(value,0,1); sendPD("hpVol",hpVol); broadcast({type:"hpVol",value:hpVol}); break; }
    case "fxReturn":  { fxReturn=clamp(value,0,1); sendPD("fxReturn",fxReturn); broadcast({type:"fxReturn",value:fxReturn}); break; }
    case "masterMute": { broadcast({type:"masterMute",value:!!value}); break; }
    case "masterPan":  { broadcast({type:"masterPan",value}); break; }
    case "recStart":   { startRecording(); break; }
    case "recStop":    { stopRecording(); break; }
    default: console.warn("Onbekend bericht type:", type);
  }
}

function updateAllGates() {
  CHANNELS.forEach(ch => sendPD(`ch${ch.index}-gate`, computeGate(ch.index)));
}

function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

// ─── Start ─────────────────────────────────────────────────────────────────
httpServer.listen(WS_PORT, () => {
  console.log("TouchLab Mixer Bridge");
  console.log(`Config:     ${configPath} (${N} kanalen)`);
  console.log(`Sessie:     ${sessionName}`);
  console.log(`WebSocket:  ws://localhost:${WS_PORT}`);
  console.log(`Downloads:  http://localhost:${WS_PORT}/recordings`);
  console.log(`Opnames in: ${REC_DIR}`);
  console.log("─".repeat(40));
});

connectToPD();
