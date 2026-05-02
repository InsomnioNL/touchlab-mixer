/**
 * TouchLab Mixer Bridge — met opname functie en sampler (TTB) ondersteuning
 */

const dgram   = require("dgram");
const net     = require("net");
const fs      = require("fs");
const path    = require("path");
const http    = require("http");
const { spawn, execSync } = require("child_process");
const { WebSocketServer } = require("ws");
const trigger = require("./trigger"); // TRIGGER-FEATURE-V1

// ─── Config laden ──────────────────────────────────────────────────────────
const configPath = process.argv[2] || "session.json";
const SESSIONS_DIR = path.join(path.dirname(path.resolve(configPath)), "sessions");

// Eerst de verse session.json (TERMINAL-default of handmatige) inlezen om de
// sessienaam te bepalen. Dan kijken of er een lokale werkversie bestaat onder
// sessions/<sessienaam>.json — die wint.
function loadSessionAtStartup() {
  var raw = JSON.parse(fs.readFileSync(configPath, "utf8"));
  var sname = raw.session_name || raw.session || path.basename(configPath, ".json");
  var workPath = path.join(SESSIONS_DIR, sanitizeSessionName(sname) + ".json");
  if (fs.existsSync(workPath)) {
    try {
      var work = JSON.parse(fs.readFileSync(workPath, "utf8"));
      // Werkversie schrijven naar session.json zodat alles ervan uitgaat.
      var tmp = configPath + ".tmp";
      fs.writeFileSync(tmp, JSON.stringify(work, null, 2), "utf8");
      fs.renameSync(tmp, configPath);
      console.log(`↺  Lokale werkversie geladen uit sessions/${sanitizeSessionName(sname)}.json`);
      return work;
    } catch (err) {
      console.warn(`⚠  Werkversie lezen mislukt, val terug op default: ${err.message}`);
    }
  } else {
    console.log(`◦  Geen lokale werkversie voor "${sname}" — TERMINAL-default in gebruik`);
  }
  return raw;
}

function sanitizeSessionName(name) {
  return String(name).trim().replace(/[\/\\:*?"<>|]/g, "_").replace(/\s+/g, "-");
}

const cfg = loadSessionAtStartup();

const sessionName    = cfg.session_name || cfg.session || path.basename(configPath, ".json");
const PD_FUDI_PORT   = cfg.osc_receive_port || 9000;
const VU_LISTEN_PORT = cfg.vu_send_port     || 9001;
const WS_PORT        = cfg.ws_port          || 8080;
const CHANNELS       = cfg.channels;
const N              = CHANNELS.length;
const REC_DIR        = cfg.recordings_path  || path.join(process.env.HOME, "recordings");
const TIMEMACHINE    = cfg.recording && cfg.recording.prebuffer ? cfg.recording.prebuffer : 0;

// Sampler (TTB) config
const SAMPLER_CFG     = cfg.sampler || {};
const SAMPLER_ENABLED = !!SAMPLER_CFG.enabled;
const SAMPLER_FUDI    = SAMPLER_CFG.fudi_port   || 9002;
const SAMPLER_STAT    = SAMPLER_CFG.status_port || 9003;
const SAMPLER_SLOTS   = SAMPLER_CFG.slots       || 8;

// Zorg dat recordings map en sessions-archief bestaan
if (!fs.existsSync(REC_DIR)) fs.mkdirSync(REC_DIR, { recursive: true });
if (!fs.existsSync(SESSIONS_DIR)) fs.mkdirSync(SESSIONS_DIR, { recursive: true });

// ─── State ─────────────────────────────────────────────────────────────────
const state = {};
CHANNELS.forEach(ch => {
  // === SAFETY-VOL-V1: state ===
    state[ch.index] = { name: ch.name, vol: 0, pan: 0.5, mute: false, solo: false, fx: 0.0, vu: -100 };
});
// === MASTER-PAN-BRIDGE-V1: state ===
// === SAFETY-VOL-V1: master-decl ===
let masterVol = 0, hpVol = 0, masterPan = 0.5, fxReturn = 0.0, masterVu = -100, masterVuL = -100, masterVuR = -100;

// ─── Sampler state ─────────────────────────────────────────────────────────
// Per slot een snapshot van wat de frontend moet weten. State (idle/recording/
// playing) wordt bijgewerkt via sampler-status events van Pd. Overige waarden
// (vol, speed, trim, autotrim-params) worden bijgewerkt als de frontend ze zet.
const samplerState = {};
for (let i = 1; i <= SAMPLER_SLOTS; i++) {
  samplerState[i] = {
    slot: i,
    state: "idle",              // idle | recording | playing
    source: "ch1",              // ch1..chN of master
    vol: 0.8,
    speed: 1.0,
    trimStart: 0,
    trimEnd: 0,
    autotrimThreshold: -40,
    autotrimPreroll: 50,
    lastEvent: null,
  };
}

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

  // === WAVEFORM-SAMPLES-ROUTE-V1: serve sample-files for waveform display ===
  if (url.startsWith("/samples/")) {
    const filename = decodeURIComponent(url.slice(9));
    const samplesDir = cfg.ttb?.samples_dir || "samples";
    const fullSamplesDir = path.isAbsolute(samplesDir) ? samplesDir : path.join(process.cwd(), samplesDir);
    const filepath = path.join(fullSamplesDir, path.basename(filename));
    if (fs.existsSync(filepath)) {
      res.writeHead(200, {
        "Content-Type": "audio/wav",
        "Access-Control-Allow-Origin": "*",
        "Content-Length": fs.statSync(filepath).size
      });
      fs.createReadStream(filepath).pipe(res);
    } else {
      res.writeHead(404); res.end("Sample niet gevonden");
    }
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

// ─── PD FUDI (mixer, TCP) ──────────────────────────────────────────────────
let pdSocket = null, pdReady = false;
let pdReconnectTimer = null;
let pdBackoffMs = 1000;          // start: 1s
const PD_BACKOFF_MAX = 30000;    // cap: 30s

function scheduleReconnectPD() {
  if (pdReconnectTimer) return;  // er staat er al één; geen dubbele timers
  pdReconnectTimer = setTimeout(() => {
    pdReconnectTimer = null;
    connectToPD();
  }, pdBackoffMs);
  pdBackoffMs = Math.min(pdBackoffMs * 2, PD_BACKOFF_MAX);
}

function connectToPD() {
  // oude socket netjes opruimen vóór nieuwe poging
  if (pdSocket) { try { pdSocket.destroy(); } catch (e) {} pdSocket = null; }

  pdSocket = net.connect(PD_FUDI_PORT, "127.0.0.1", () => {
    pdReady = true;
    pdBackoffMs = 1000;          // reset bij succes
    console.log(`✓  Verbonden met PD op poort ${PD_FUDI_PORT}`);
    initPD();
  });
  pdSocket.on("error", err => {
    if (pdReady) console.warn(`⚠  PD: ${err.message}`);  // eerste error per cyclus loggen
    pdReady = false;
    scheduleReconnectPD();
  });
  pdSocket.on("close", () => {
    pdReady = false;
    scheduleReconnectPD();
  });
}

function sendPD(receiver, ...args) {
  if (!pdReady || !pdSocket) return;
  pdSocket.write(`; ${receiver} ${args.join(" ")};\n`);
}

function initPD() {
  CHANNELS.forEach(ch => {
    const s = state[ch.index];
    // === SAFETY-VOL-V1: init ===
    // ch${ch.index}-vol/masterVol/hpVol weggehaald: komen pas bij recall.
    sendPD(`ch${ch.index}-pan`, s.pan);
    sendPD(`ch${ch.index}-gate`, computeGate(ch.index));
    sendPD(`ch${ch.index}-fx`, s.fx);
  });
  sendPD("fxReturn", fxReturn);
  console.log("✓  Beginwaarden naar PD gestuurd");
  // Na mixer-init de TTB-samples laden in de sampler-slots
  ensureSlotEntries();
  setTimeout(loadTTBSamples, 300);
}

// === ENSURE-SLOT-ENTRIES-V1 ===
// Zorgt dat cfg.ttb.slots voor elke slot 1..SAMPLER_SLOTS een entry heeft.
// Default-entries zijn minimaal: {slot, label, vol, color} - geen 'file'-veld,
// zodat loadTTBSamples ze netjes skipt (geen sampler-load voor lege slots).
// Pas zodra een rec gebeurt en history zich opbouwt, krijgt zo'n slot een file.
function ensureSlotEntries() {
  if (!SAMPLER_ENABLED) return;
  if (!cfg.ttb) cfg.ttb = {};
  if (!Array.isArray(cfg.ttb.slots)) cfg.ttb.slots = [];

  const present = new Set(cfg.ttb.slots.map(s => s.slot).filter(n => typeof n === "number"));
  let added = 0;
  for (let i = 1; i <= SAMPLER_SLOTS; i++) {
    if (!present.has(i)) {
      cfg.ttb.slots.push({
        slot: i,
        label: `SLOT ${i}`,
        vol: 0.8,
        color: "neutral",
      });
      added++;
    }
  }
  if (added > 0) {
    console.log(`+  ${added} slot-entries toegevoegd aan cfg.ttb.slots (default placeholders)`);
  }
}

// ─── TTB sample-loader ─────────────────────────────────────────────────────
// Leest ttb.slots uit session.json en laadt per slot de samples in Pd.
// Pad is relatief tot de werkmap van Pd (meestal de map van de .pd patch),
// of absoluut als je een volledig pad opgeeft.
function loadTTBSamples() {
  if (!SAMPLER_ENABLED) return;
  const slots = Array.isArray(cfg.ttb?.slots) ? cfg.ttb.slots : [];
  if (slots.length === 0) return;

  const samplesDir = cfg.ttb?.samples_dir || "samples";
  let loaded = 0;
  slots.forEach(s => {
    if (!s.slot || !s.file) return;
    const filePath = path.isAbsolute(s.file) ? s.file : path.posix.join(samplesDir, s.file);
    sendSampler("sampler-load", s.slot, filePath);
    if (typeof s.vol === "number") {
      samplerState[s.slot].vol = s.vol;
      sendSampler("sampler-vol", s.slot, s.vol);
    }
    loaded++;
  });
  console.log(`✓  ${loaded} TTB-samples geladen`);
}

// === REC-HISTORY-V1 ===
// Bij rec-stop: kopieert slotN.wav naar slotN_<timestamp>.wav en voegt
// een history-entry toe aan cfg.ttb.slots[N]. Persisteert sessie via
// saveSessionToDisk. Faalt zacht bij disk-fouten (warning, geen crash).
function archiveRecording(slot) {
  if (!SAMPLER_ENABLED) return;

  const samplesDir = cfg.ttb?.samples_dir || "samples";
  const fullSamplesDir = path.isAbsolute(samplesDir) ? samplesDir : path.join(process.cwd(), samplesDir);
  const srcPath = path.join(fullSamplesDir, `slot${slot}.wav`);

  // Lokale tijd in sortbaar formaat: YYYY-MM-DD-HH-MM-SS
  const d = new Date();
  const pad = n => String(n).padStart(2, "0");
  const ts = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}-${pad(d.getHours())}-${pad(d.getMinutes())}-${pad(d.getSeconds())}`;
  const archiveName = `slot${slot}_${ts}.wav`;
  const archivePath = path.join(fullSamplesDir, archiveName);

  // Duration: ms verschil tussen recording-start en nu
  const startTs = samplerState[slot]?.recStartTs;
  const durationSec = startTs ? Math.round((Date.now() - startTs) / 100) / 10 : null;

  try {
    fs.copyFileSync(srcPath, archivePath);
  } catch (err) {
    console.warn(`⚠  Kon ${srcPath} niet archiveren: ${err.message}`);
    return;
  }

  // History-entry toevoegen aan cfg.ttb.slots[slot]
  const entry = {
    filename: archiveName,
    recorded_at: d.toISOString(),
  };
  if (durationSec != null) entry.duration_seconds = durationSec;

  const slotEntry = cfg.ttb.slots.find(s => s.slot === slot);
  if (!slotEntry) {
    console.warn(`⚠  archiveRecording: slot ${slot} niet in cfg.ttb.slots (zou niet moeten kunnen na ensureSlotEntries)`);
    return;
  }
  if (!Array.isArray(slotEntry.history)) slotEntry.history = [];
  slotEntry.history.push(entry);

  // Persisteer naar disk
  try {
    saveSessionToDisk(cfg, null, { skipReload: true });
    console.log(`+  Slot ${slot} archief: ${archiveName}${durationSec != null ? ` (${durationSec}s)` : ""}`);
  } catch (err) {
    console.warn(`⚠  Sessie-save na archive faalde: ${err.message}`);
  }
}

// ─── Sampler FUDI (TTB, UDP) ───────────────────────────────────────────────
// Outbound:   bridge → Pd op SAMPLER_FUDI (9002) als text-FUDI in UDP packets
// Inbound:    Pd → bridge op SAMPLER_STAT (9003) met sampler-status events
const samplerOut = dgram.createSocket("udp4");
const samplerIn  = dgram.createSocket("udp4");

function sendSampler(cmd, ...args) {
  if (!SAMPLER_ENABLED) return;
  const msg = Buffer.from(`${cmd} ${args.join(" ")};\n`);
  samplerOut.send(msg, SAMPLER_FUDI, "127.0.0.1", err => {
    if (err) console.warn(`⚠  Sampler TX: ${err.message}`);
  });
}

samplerIn.on("error", err => console.warn(`⚠  Sampler RX: ${err.message}`));
// === SAMPLER-EVENT-DEDUPE-V1 ===
// Pd dupliceert sommige status-broadcasts (~9x per event); de oorzaak
// zit in de patch-architectuur (open issue). Bridge dedupt hier:
// hetzelfde (slot, event) binnen 500ms wordt slechts 1x verwerkt.
const samplerEventLastSeen = new Map();  // key: "slot:event", value: timestamp
const SAMPLER_EVENT_DEDUPE_MS = 500;

samplerIn.on("message", buf => {
  const line = buf.toString().replace(/;\s*$/,"").trim();
  if (!line) return;
  const parts = line.split(/\s+/);
  // === LIST-PREFIX-STRIP-V1 ===
  // Pd's [fudiformat] serializeert Pd-lists als "list <items>" -
  // het "list"-prefix moet weg vóór de sampler-status-check, anders
  // worden alle status-events gedropt.
  if (parts[0] === "list") parts.shift();
  if (parts[0] !== "sampler-status" || parts.length < 3) return;

  const slot = parseInt(parts[1]);
  if (!samplerState[slot]) return;

  const event = parts[2];
  const extra = parts.slice(3).join(" ") || null;

  // === SAMPLER-EVENT-DEDUPE-V1 ===
  const dedupeKey = `${slot}:${event}`;
  const now = Date.now();
  const lastSeen = samplerEventLastSeen.get(dedupeKey);
  if (lastSeen && (now - lastSeen) < SAMPLER_EVENT_DEDUPE_MS) {
    return;  // duplicate, drop
  }
  samplerEventLastSeen.set(dedupeKey, now);

  // State-machine: mappen van event naar state-veld
  switch (event) {
    case "recording":   samplerState[slot].state = "recording"; samplerState[slot].recStartTs = Date.now(); break;
    case "rec-stopped": samplerState[slot].state = "idle"; archiveRecording(slot); break;
    case "playing":     samplerState[slot].state = "playing";   break;
    case "stopped":     samplerState[slot].state = "idle";      break;
    case "input":       if (extra) samplerState[slot].source = extra; break;
    // autotrim-done en overige events: geen state-wijziging, alleen event doorzetten
  }
  samplerState[slot].lastEvent = event;

  broadcast({
    type: "samplerStatus",
    slot,
    event,
    state: samplerState[slot].state,
    source: samplerState[slot].source,
    extra,
  });
});

// ─── VU ────────────────────────────────────────────────────────────────────
const vuServer = dgram.createSocket("udp4");
vuServer.bind(VU_LISTEN_PORT, () => console.log(`✓  VU luisteren op UDP ${VU_LISTEN_PORT}`));
vuServer.on("message", buf => {
  const parts = buf.toString().replace(/;\s*$/, "").trim().split(/\s+/);
  // === VU-LIST-PREFIX-STRIP-V1 ===
  // Pd's [fudiformat] prefixt list-messages met 'list' - moet weg.
  if (parts[0] === "list") parts.shift();
  if (parts[0] !== "vu" || parts.length < 3) return;
  const who = parts[1], val = parseFloat(parts[2]);
  // === BRIDGE-STEREO-VU-V1 ===
  if (who === "masterL") { masterVuL = val; masterVu = (masterVuL + masterVuR) / 2; }
  else if (who === "masterR") { masterVuR = val; masterVu = (masterVuL + masterVuR) / 2; }
  else if (who === "master") masterVu = val;  // backward compat
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
    sampler: SAMPLER_ENABLED ? { enabled: true, slots: Object.values(samplerState) } : null,
  }));
  ws.on("message", raw => {
    try {
      handleFrontendMessage(JSON.parse(raw), ws);
    } catch (err) {
      console.warn(`⚠  Bericht-afhandeling: ${err.message}`);
    }
  });
  ws.on("close", () => { wsClients.delete(ws); console.log(`-  Frontend verbroken (${wsClients.size} clients)`); });
});

function broadcast(obj) {
  const data = JSON.stringify(obj);
  wsClients.forEach(ws => { if (ws.readyState === 1) ws.send(data); });
}

function broadcastVU() {
  broadcast({ type: "vu", channels: CHANNELS.map(ch => ({ index: ch.index, vu: state[ch.index].vu })), masterVu, masterVuL, masterVuR });
}

// ─── Frontend berichten ─────────────────────────────────────────────────────
function handleFrontendMessage(msg, ws) {
  const { type, channel, value } = msg;
  switch (type) {
    // Mixer kanalen
    case "volume": { const v = clamp(value,0,1); state[channel].vol=v; sendPD(`ch${channel}-vol`,v); broadcast({type:"volume",channel,value:v}); break; }
    case "pan":    { const v = clamp(value,0,1); state[channel].pan=v; sendPD(`ch${channel}-pan`,v); broadcast({type:"pan",channel,value:v}); break; }
    case "mute":   { state[channel].mute=!!value; updateAllGates(); broadcast({type:"mute",channel,value:state[channel].mute}); break; }
    case "solo":   { state[channel].solo=!!value; updateAllGates(); broadcast({type:"solo",channel,value:state[channel].solo}); break; }
    case "fx":     { const v = clamp(value,0,1); state[channel].fx=v; sendPD(`ch${channel}-fx`,v); broadcast({type:"fx",channel,value:v}); break; }
    // Master
    case "masterVol": { masterVol=clamp(value,0,1); sendPD("masterVol",masterVol); broadcast({type:"masterVol",value:masterVol}); break; }
    case "hpVol":     { hpVol=clamp(value,0,1); sendPD("hpVol",hpVol); broadcast({type:"hpVol",value:hpVol}); break; }
    case "fxReturn":  { fxReturn=clamp(value,0,1); sendPD("fxReturn",fxReturn); broadcast({type:"fxReturn",value:fxReturn}); break; }
    case "masterMute": { broadcast({type:"masterMute",value:!!value}); break; }
    case "masterPan":  { masterPan=clamp(value,0,1); sendPD("masterPan",masterPan); broadcast({type:"masterPan",value:masterPan}); break; } // === MASTER-PAN-BRIDGE-V1: handler ===
    // Opname (jack_capture)
    case "recStart":   { startRecording(); break; }
    case "recStop":    { stopRecording(); break; }
    // Sampler (TTB) — transport
    case "samplerRecStart": {
      const samplesDir = cfg.ttb?.samples_dir || "samples";
      const fullSamplesDir = path.isAbsolute(samplesDir) ? samplesDir : path.join(process.cwd(), samplesDir);
      const recPath = path.join(fullSamplesDir, `slot${msg.slot}.wav`);
      sendSampler("sampler-rec-path", msg.slot, recPath);
      sendSampler("sampler-rec-start", msg.slot);
      break;
    }
    case "samplerRecStop":  { sendSampler("sampler-rec-stop",  msg.slot); break; }
    case "samplerPlay":     { sendSampler("sampler-play",      msg.slot); break; }
    case "samplerStop":     { sendSampler("sampler-stop",      msg.slot); break; }
    // Sampler — per-slot parameters (state tracking + echo broadcast)
    case "samplerVol": {
      const v = clamp(msg.value, 0, 1);
      if (samplerState[msg.slot]) samplerState[msg.slot].vol = v;
      sendSampler("sampler-vol", msg.slot, v);
      broadcast({ type: "samplerVol", slot: msg.slot, value: v });
      break;
    }
    case "samplerMasterVol": {
      // Master-vol: per slot een eigen [r sampler-master-vol] -> [pack 0 20] -> [line~] -> *~ chain
      const v = clamp(msg.value, 0, 1);
      sendSampler("sampler-master-vol", v);
      broadcast({ type: "samplerMasterVol", value: v });
      break;
    }
    // === TTB-ROUTE-BRIDGE-V1 ===
    case "ttbRoute": {
      // value: local | live - mutually exclusive route-switch
      const route = (msg.value === "local") ? "local" : "live";
      const localOn = (route === "local") ? 1 : 0;
      const liveOn  = (route === "live")  ? 1 : 0;
      sendPD("ttb-route-local", localOn);
      sendPD("ttb-route-live",  liveOn);
      broadcast({ type: "ttbRoute", value: route });
      break;
    }
    case "samplerSpeed": {
      const v = clamp(msg.value, 0.1, 4);
      if (samplerState[msg.slot]) samplerState[msg.slot].speed = v;
      sendSampler("sampler-speed", msg.slot, v);
      broadcast({ type: "samplerSpeed", slot: msg.slot, value: v });
      break;
    }
    case "samplerLoad": {
      // msg.path — pad naar .wav relatief of absoluut
      sendSampler("sampler-load", msg.slot, msg.path);
      broadcast({ type: "samplerLoad", slot: msg.slot, path: msg.path });
      break;
    }
    case "samplerRouterInput": {
      // msg.source — "ch1".."chN" of "master"
      if (samplerState[msg.slot]) samplerState[msg.slot].source = msg.source;
      sendSampler("sampler-router-input", msg.slot, msg.source);
      broadcast({ type: "samplerRouterInput", slot: msg.slot, source: msg.source });
      break;
    }
    case "samplerTrim": {
      if (samplerState[msg.slot]) samplerState[msg.slot].trimStart = msg.value;
      sendSampler("sampler-trim", msg.slot, msg.value);
      broadcast({ type: "samplerTrim", slot: msg.slot, value: msg.value });
      break;
    }
    case "samplerTrimEnd": {
      if (samplerState[msg.slot]) samplerState[msg.slot].trimEnd = msg.value;
      sendSampler("sampler-trim-end", msg.slot, msg.value);
      broadcast({ type: "samplerTrimEnd", slot: msg.slot, value: msg.value });
      break;
    }
    case "samplerAutotrim": { sendSampler("sampler-autotrim", msg.slot); break; }
    case "samplerAutotrimThreshold": {
      if (samplerState[msg.slot]) samplerState[msg.slot].autotrimThreshold = msg.value;
      sendSampler("sampler-autotrim-threshold", msg.slot, msg.value);
      broadcast({ type: "samplerAutotrimThreshold", slot: msg.slot, value: msg.value });
      break;
    }
    case "samplerAutotrimPreroll": {
      if (samplerState[msg.slot]) samplerState[msg.slot].autotrimPreroll = msg.value;
      sendSampler("sampler-autotrim-preroll", msg.slot, msg.value);
      broadcast({ type: "samplerAutotrimPreroll", slot: msg.slot, value: msg.value });
      break;
    }
    // Sessie-config opslaan (musici-edits naar disk)
    case "saveSession": {
      saveSessionToDisk(msg.config, ws);
      break;
    }
    // Sample-bestanden in samples-map opvragen
    case "listSamples": {
      var files = listSampleFiles();
      console.log(`✓  listSamples: ${files.length} bestand(en) gevonden`);
      if (ws) ws.send(JSON.stringify({
        type: "sampleList",
        files: files,
      }));
      break;
    }
    default: console.warn("Onbekend bericht type:", type);
  }
}

function updateAllGates() {
  CHANNELS.forEach(ch => sendPD(`ch${ch.index}-gate`, computeGate(ch.index)));
}

function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

// ─── Sessie-config schrijven en samples lijsten ────────────────────────────
// Atomic write: eerst naar tijdelijk bestand, dan rename. Voorkomt corrupte
// session.json als het schrijven onderbroken wordt.
function saveSessionToDisk(newConfig, ws, opts) {
  if (!newConfig || typeof newConfig !== "object") {
    if (ws) ws.send(JSON.stringify({type:"saveSessionResult", ok:false, error:"invalid config"}));
    return;
  }
  // === SKIP-RELOAD-V1 ===
  // Interne aanroepers (archiveRecording) hebben alleen history-state
  // bijgewerkt — Pd hoeft niets opnieuw te laden.
  var skipReload = opts && opts.skipReload === true;
  try {
    // Als de UI alleen het ttb-deel stuurt (__ttb_only flag), merge dat in cfg
    // === SAVESESSION-SELFREF-V1 ===
    // Als newConfig === cfg (zelf-referentie vanuit interne aanroepers
    // zoals archiveRecording), deep-copy om data-loss te voorkomen bij
    // de delete-then-reassign-cyclus hieronder.
    var fullConfig;
    if (newConfig === cfg) {
      fullConfig = JSON.parse(JSON.stringify(cfg));
    } else if (newConfig.__ttb_only && newConfig.ttb) {
      fullConfig = JSON.parse(JSON.stringify(cfg));
      fullConfig.ttb = newConfig.ttb;
    } else {
      fullConfig = newConfig;
    }
    // 1. Schrijf naar de actieve session.json (atomic via .tmp + rename)
    var tmp = configPath + ".tmp";
    fs.writeFileSync(tmp, JSON.stringify(fullConfig, null, 2), "utf8");
    fs.renameSync(tmp, configPath);
    // 2. Schrijf óók een kopie naar sessions/<sessienaam>.json (lokaal werkarchief)
    var sname = fullConfig.session_name || fullConfig.session || sessionName;
    var workPath = path.join(SESSIONS_DIR, sanitizeSessionName(sname) + ".json");
    var workTmp  = workPath + ".tmp";
    fs.writeFileSync(workTmp, JSON.stringify(fullConfig, null, 2), "utf8");
    fs.renameSync(workTmp, workPath);
    // Update onze in-memory cfg en TTB-state
    Object.keys(cfg).forEach(k => delete cfg[k]);
    Object.assign(cfg, fullConfig);
    console.log(`✓  Sessie opgeslagen naar ${configPath} + sessions/${sanitizeSessionName(sname)}.json`);
    // Herlaad TTB-samples in Pd op basis van nieuwe config
    if (SAMPLER_ENABLED && !skipReload) { ensureSlotEntries(); loadTTBSamples(); }
    // Bevestig naar afzender, en broadcast naar andere clients
    if (ws) ws.send(JSON.stringify({type:"saveSessionResult", ok:true}));
    broadcast({type:"sessionUpdated", ttb: cfg.ttb || null});
  } catch (err) {
    console.warn(`⚠  Sessie opslaan mislukt: ${err.message}`);
    if (ws) ws.send(JSON.stringify({type:"saveSessionResult", ok:false, error:err.message}));
  }
}

function listSampleFiles() {
  var samplesDir = cfg.ttb && cfg.ttb.samples_dir ? cfg.ttb.samples_dir : "samples";
  // Pad relatief tot bridge-werkmap
  var fullDir = path.isAbsolute(samplesDir) ? samplesDir : path.join(process.cwd(), samplesDir);
  if (!fs.existsSync(fullDir)) return [];
  try {
    return fs.readdirSync(fullDir)
      .filter(f => /\.(wav|aif|aiff)$/i.test(f))
      .sort();
  } catch (err) {
    console.warn(`⚠  Sample-lijst lezen mislukt: ${err.message}`);
    return [];
  }
}

// ─── Start ─────────────────────────────────────────────────────────────────
httpServer.listen(WS_PORT, () => {
  console.log("TouchLab Mixer Bridge");
  console.log(`Config:     ${configPath} (${N} kanalen)`);
  console.log(`Sessie:     ${sessionName}`);
  console.log(`WebSocket:  ws://localhost:${WS_PORT}`);
  console.log(`Downloads:  http://localhost:${WS_PORT}/recordings`);
  console.log(`Opnames in: ${REC_DIR}`);
  // Tel werkversies in archief
  try {
    var workCount = fs.readdirSync(SESSIONS_DIR).filter(f => /\.json$/.test(f)).length;
    console.log(`Sessies:    ${workCount} werkversie(s) in ${path.relative(process.cwd(), SESSIONS_DIR) || 'sessions'}/`);
  } catch (e) {}
  if (SAMPLER_ENABLED) {
    console.log(`Sampler:    ${SAMPLER_SLOTS} slots · cmd→UDP ${SAMPLER_FUDI} · status←UDP ${SAMPLER_STAT}`);
  } else {
    console.log(`Sampler:    uitgeschakeld (zet cfg.sampler.enabled op true)`);
  }
  console.log("─".repeat(40));
});

connectToPD();
trigger.start(); // TRIGGER-START-V1
if (SAMPLER_ENABLED) {
  samplerIn.bind(SAMPLER_STAT, () => console.log(`✓  Sampler status luisteren op UDP ${SAMPLER_STAT}`));
}
