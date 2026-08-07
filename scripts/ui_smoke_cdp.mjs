// Minimal Chrome DevTools Protocol driver (no external deps) to verify that
// every route renders without a blank-screen crash against the live preview.
import { writeFileSync, mkdirSync } from "node:fs";

const BASE = "http://127.0.0.1:5173";
const OUT = "/tmp/cursor/artifacts/p0-verify";
mkdirSync(OUT, { recursive: true });

const EMAIL = process.env.DEMO_EMAIL || "founder@lumora.local";
const PASSWORD = process.env.DEMO_PASSWORD || "lumora-demo-2026";

const version = await (await fetch("http://127.0.0.1:9222/json/version")).json();
const wsUrl = version.webSocketDebuggerUrl;

const ws = new WebSocket(wsUrl);
let nextId = 1;
const pending = new Map();
const sessions = {};

function send(method, params = {}, sessionId) {
  const id = nextId++;
  const msg = { id, method, params };
  if (sessionId) msg.sessionId = sessionId;
  ws.send(JSON.stringify(msg));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

await new Promise((r) => (ws.onopen = r));
ws.onmessage = (ev) => {
  const data = JSON.parse(ev.data);
  if (data.id && pending.has(data.id)) {
    const { resolve, reject } = pending.get(data.id);
    pending.delete(data.id);
    if (data.error) reject(new Error(JSON.stringify(data.error)));
    else resolve(data.result);
  }
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Attach to a fresh page target.
const { targetId } = await send("Target.createTarget", { url: "about:blank" });
const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
sessions.page = sessionId;
await send("Page.enable", {}, sessionId);
await send("Runtime.enable", {}, sessionId);

async function evaluate(expression, awaitPromise = true) {
  const res = await send(
    "Runtime.evaluate",
    { expression, awaitPromise, returnByValue: true },
    sessionId,
  );
  if (res.exceptionDetails) {
    throw new Error(res.exceptionDetails.exception?.description || "eval error");
  }
  return res.result.value;
}

async function navigate(url) {
  await send("Page.navigate", { url }, sessionId);
  await sleep(1500);
}

async function shot(name) {
  const { data } = await send(
    "Page.captureScreenshot",
    { format: "png", captureBeyondViewport: true },
    sessionId,
  );
  writeFileSync(`${OUT}/${name}.png`, Buffer.from(data, "base64"));
}

async function report() {
  return evaluate(`(() => ({
    textLen: document.body ? document.body.innerText.length : 0,
    crash: !!document.querySelector('.app-crash'),
    errorState: !!document.querySelector('.error-state'),
    footer: (document.querySelector('.sidebar-foot strong')||{}).innerText || null,
    heading: (document.querySelector('main h1, main h2')||{}).innerText || null,
  }))()`);
}

// Boot app, log in, seed session, reload.
await navigate(BASE);
await send(
  "Emulation.setDeviceMetricsOverride",
  { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false },
  sessionId,
);
const loginInfo = await evaluate(`(async () => {
  const r = await fetch('/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email:${JSON.stringify(EMAIL)}, password:${JSON.stringify(PASSWORD)}})});
  if (!r.ok) return { ok:false, status:r.status, body: await r.text() };
  const auth = await r.json();
  const ws = await (await fetch('/api/workspaces', {headers:{Authorization:'Bearer '+auth.access_token}})).json();
  sessionStorage.setItem('lumora.missionControl.session', JSON.stringify({token:auth.access_token, workspaceId: ws[0].id, email: auth.email}));
  return { ok:true, workspaces: ws.length };
})()`);
console.log("login:", JSON.stringify(loginInfo));
if (!loginInfo.ok) { console.log("LOGIN FAILED"); process.exit(2); }

await navigate(BASE);
await sleep(1200);

const routes = ["Dashboard", "Mission Control", "Review Queue", "Pipelines", "Workers", "Customers", "Leads", "Analytics", "Billing", "Settings"];
const missionTabs = ["Overview", "Timeline", "Live logs", "AI assistant", "Content"];

const results = [];
let index = 0;
for (const label of routes) {
  const clicked = await evaluate(`(() => {
    const nav = document.querySelector('nav[aria-label="Primary navigation"]');
    if (!nav) return false;
    const btn = [...nav.querySelectorAll('button')].find(b => b.innerText.trim().startsWith(${JSON.stringify(label)}));
    if (!btn) return false;
    btn.click();
    return true;
  })()`);
  await sleep(1300);
  const rep = await report();
  await shot(`${String(index).padStart(2, "0")}-${label.replace(/\s+/g, "-").toLowerCase()}`);
  results.push({ label, clicked, ...rep });
  index++;

  if (label === "Mission Control") {
    for (const tab of missionTabs) {
      await evaluate(`(() => {
        const tabs = document.querySelector('.view-tabs');
        if (!tabs) return false;
        const btn = [...tabs.querySelectorAll('button')].find(b => b.innerText.trim() === ${JSON.stringify(tab)});
        if (btn) btn.click();
        return !!btn;
      })()`);
      await sleep(1200);
      const trep = await report();
      await shot(`${String(index).padStart(2, "0")}-mission-${tab.replace(/\s+/g, "-").toLowerCase()}`);
      results.push({ label: `Mission/${tab}`, ...trep });
      index++;
    }
  }
}

// Mobile pass.
await send(
  "Emulation.setDeviceMetricsOverride",
  { width: 390, height: 844, deviceScaleFactor: 2, mobile: true },
  sessionId,
);
await navigate(BASE);
await sleep(1200);
await evaluate(`(() => { const b=[...document.querySelectorAll('button')].find(x=>/open navigation/i.test(x.getAttribute('aria-label')||'')); if(b)b.click(); return !!b; })()`);
await sleep(500);
await shot("90-mobile-nav-open");
const mrep = await report();
results.push({ label: "mobile-dashboard", ...mrep });

writeFileSync(`${OUT}/results.json`, JSON.stringify(results, null, 2));
const crashes = results.filter((r) => r.crash || r.textLen === 0);
console.log("ROUTES:", results.length);
console.log("BLANK/CRASH:", crashes.length);
for (const r of results) {
  console.log(`  ${r.crash ? "CRASH" : r.textLen === 0 ? "BLANK" : "ok   "} | ${r.label} | textLen=${r.textLen} | footer=${r.footer ?? "-"}`);
}
process.exit(crashes.length === 0 ? 0 : 1);
