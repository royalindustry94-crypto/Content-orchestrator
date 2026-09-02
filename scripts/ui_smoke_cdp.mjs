// Minimal Chrome DevTools Protocol driver (no external deps) to verify that
// every route renders without a blank-screen crash against the live preview.
import { writeFileSync, mkdirSync } from "node:fs";

const BASE = process.env.UI_SMOKE_BASE ?? "http://127.0.0.1:5173";
const OUT = process.env.UI_SMOKE_OUT ?? "/tmp/cursor/artifacts/p0-verify";
mkdirSync(OUT, { recursive: true });

const EMAIL = process.env.DEMO_EMAIL;
const PASSWORD = process.env.DEMO_PASSWORD;
if (!EMAIL || !PASSWORD) {
  throw new Error("DEMO_EMAIL and DEMO_PASSWORD are required for UI smoke credentials");
}

const version = await (await fetch("http://127.0.0.1:9222/json/version")).json();
const wsUrl = version.webSocketDebuggerUrl;

const ws = new WebSocket(wsUrl);
let nextId = 1;
const pending = new Map();
const sessions = {};
const consoleProblems = [];
const uncaughtExceptions = [];

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
  if (data.method === "Runtime.exceptionThrown") {
    uncaughtExceptions.push(data.params.exceptionDetails?.exception?.description || data.params.exceptionDetails?.text || "Unknown exception");
  }
  if (data.method === "Runtime.consoleAPICalled" && ["error", "warning"].includes(data.params.type)) {
    const text = data.params.args
      .map((arg) => arg.value ?? arg.description ?? "")
      .join(" ");
    consoleProblems.push({ type: data.params.type, text });
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

async function setLabeledField(label, value) {
  const changed = await evaluate(`(() => {
    const element = [...document.querySelectorAll('input, textarea, select')]
      .find(item => item.getAttribute('aria-label') === ${JSON.stringify(label)});
    if (!element) return false;
    const prototype = element instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : element instanceof HTMLSelectElement
        ? HTMLSelectElement.prototype
        : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
    setter.call(element, ${JSON.stringify(value)});
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  })()`);
  if (!changed) throw new Error(`Unable to find setup field: ${label}`);
  await sleep(120);
}

async function clickButton(label) {
  const clicked = await evaluate(`(() => {
    const button = [...document.querySelectorAll('button')]
      .find(item => (item.textContent || '').trim().includes(${JSON.stringify(label)}));
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  if (!clicked) throw new Error(`Unable to click button: ${label}`);
  await sleep(180);
}

async function report() {
  return evaluate(`(() => ({
    textLen: document.body ? document.body.innerText.length : 0,
    crash: !!document.querySelector('.app-crash'),
    errorState: !!document.querySelector('.error-state'),
    footer: (document.querySelector('.sidebar-foot strong')||{}).innerText || null,
    heading: (document.querySelector('main h1, main h2')||{}).innerText || null,
    horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth,
    conditionRows: document.querySelectorAll('#active-alerts .decision-card').length,
    financialCircles: document.querySelectorAll('.financial-overview__circle').length,
    unavailableFinancialMetrics: [...document.querySelectorAll('.financial-overview__circle strong')].filter(el => el.textContent?.trim() === 'Not connected').length,
    bankrollHeading: (document.querySelector('.financial-overview__header h3') || {}).textContent?.trim() || null,
    homeIdentityCentered: getComputedStyle(document.querySelector('.business-home__intro') || document.body).textAlign === 'center',
    bankrollCentered: getComputedStyle(document.querySelector('.financial-overview__header') || document.body).textAlign === 'center',
    researchProviderNotConfigured: /RESEARCH PROVIDER NOT CONFIGURED/i.test(document.body?.innerText || ''),
    researchOpportunityEmpty: /No opportunities yet/i.test(document.body?.innerText || ''),
    strategyProviderNotConfigured: /STRATEGY PROVIDER NOT CONFIGURED/i.test(document.body?.innerText || ''),
    strategyBusinessContextIncomplete: /BUSINESS CONTEXT INCOMPLETE/i.test(document.body?.innerText || ''),
    strategyBriefEmpty: /No Strategy Briefs yet/i.test(document.body?.innerText || ''),
    contentProviderNotConfigured: /CONTENT PROVIDER NOT CONFIGURED/i.test(document.body?.innerText || ''),
    contentBusinessContextIncomplete: /BUSINESS CONTEXT INCOMPLETE/i.test(document.body?.innerText || ''),
    contentPackageEmpty: /No Creative Packages yet/i.test(document.body?.innerText || ''),
    productionProviderNotConfigured: /PRODUCTION PROVIDER NOT CONFIGURED/i.test(document.body?.innerText || ''),
    productionJobEmpty: /No production jobs yet/i.test(document.body?.innerText || ''),
    complianceProviderNotConfigured: /COMPLIANCE PROVIDER NOT CONFIGURED/i.test(document.body?.innerText || ''),
    complianceEvidenceEmpty: /No compliance evidence yet/i.test(document.body?.innerText || ''),
    compliancePolicyFreshnessUnverified: /Policy[\\s\\S]+freshness[\\s\\S]+unverified/i.test(document.body?.innerText || ''),
    unlabeledControls: [...document.querySelectorAll('input, select, textarea')].filter(el =>
      !el.getAttribute('aria-label') &&
      !el.getAttribute('aria-labelledby') &&
      !el.closest('label') &&
      !el.getAttribute('title')
    ).length,
    setupSmallTouchTargets: [...document.querySelectorAll('.content-setup button, .content-setup input, .content-setup select, .content-setup textarea')]
      .filter(el => el.getBoundingClientRect().height < 44).length,
    businessManagerBrand: /The Business Manager/i.test(document.body?.innerText || ''),
  }))()`);
}

// Boot app, log in, seed session, reload.
await navigate(BASE);
await send(
  "Emulation.setDeviceMetricsOverride",
  { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false },
  sessionId,
);
const loginUxInitial = await evaluate(`(() => {
  const signInHeading = [...document.querySelectorAll('h1,h2')].some(el => /^sign in$/i.test((el.textContent || '').trim()));
  const loginWorkspaceField = [...document.querySelectorAll('label')].some(el => /^workspace name/i.test((el.textContent || '').trim()));
  const createButton = [...document.querySelectorAll('button')].find(el => /create account/i.test(el.textContent || ''));
  if (createButton) createButton.click();
  return { signInHeading, loginWorkspaceField };
})()`);
await sleep(100);
const signupWorkspaceField = await evaluate(`(() => {
  const found = [...document.querySelectorAll('label')].some(el => /^workspace name/i.test((el.textContent || '').trim()));
  const backButton = [...document.querySelectorAll('button')].find(el => /already have an account/i.test(el.textContent || ''));
  if (backButton) backButton.click();
  return found;
})()`);
const loginUx = { ...loginUxInitial, signupWorkspaceField };
await shot("00-auth");
const loginInfo = await evaluate(`(async () => {
  const r = await fetch('/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email:${JSON.stringify(EMAIL)}, password:${JSON.stringify(PASSWORD)}})});
  if (!r.ok) return { ok:false, status:r.status, body: await r.text() };
  const auth = await r.json();
  const ws = await (await fetch('/api/workspaces', {headers:{Authorization:'Bearer '+auth.access_token}})).json();
  sessionStorage.setItem('lumora.missionControl.session', JSON.stringify({token:auth.access_token, workspaceId: ws[0].id, email: auth.email}));
  return { ok:true, workspaces: ws.length };
})()`);
console.log("login:", JSON.stringify(loginInfo));
console.log("LOGIN UX:", JSON.stringify(loginUx));
if (!loginInfo.ok) { console.log("LOGIN FAILED"); process.exit(2); }

await send("Page.navigate", { url: BASE }, sessionId);
await sleep(80);
const launchObserved = await evaluate(`!!document.querySelector('.business-launch')`);
console.log("LAUNCH OBSERVED:", launchObserved);
if (launchObserved) await shot("00-launch");
await sleep(760);
const setupNeeded = await evaluate(
  `!![...document.querySelectorAll('h3')].find(el => /Set up content creation/i.test(el.textContent || ''))`,
);
if (setupNeeded) {
  await shot("01-setup-start");
  await clickButton("Done-for-you client");
  await setLabeledField("Business name", "Business Manager Demo Client");
  await setLabeledField("What do you sell?", "A practical content management service");
  await clickButton("Save and continue");
  await setLabeledField("Who is this content for?", "Busy small-business owners");
  await clickButton("Save and continue");
  await setLabeledField("Brand voice", "Clear, confident, practical");
  await clickButton("Save and continue");
  await setLabeledField("Primary platform", "Instagram");
  await setLabeledField("Content goal", "Build trust and generate qualified enquiries");
  await clickButton("Save and continue");
  await setLabeledField("First content topic", "Three ways to simplify weekly content planning");
  await clickButton("Create first draft");
  await sleep(1800);
}
const setupVerification = await evaluate(`(async () => {
  const session = JSON.parse(sessionStorage.getItem('lumora.missionControl.session'));
  const response = await fetch('/api/workspaces/' + session.workspaceId + '/content-profile', {
    headers: { Authorization: 'Bearer ' + session.token },
  });
  const profile = response.ok ? await response.json() : null;
  return {
    status: response.status,
    saved: !!profile,
    serviceMode: profile?.service_mode || null,
    completeView: /Content setup complete/i.test(document.body?.innerText || ''),
  };
})()`);
console.log("SETUP:", JSON.stringify(setupVerification));
if (!setupVerification.saved || !setupVerification.completeView) {
  throw new Error(`Five-step setup did not persist: ${JSON.stringify(setupVerification)}`);
}
const backendTruth = await evaluate(`(async () => {
  const session = JSON.parse(sessionStorage.getItem('lumora.missionControl.session'));
  const headers = { Authorization: 'Bearer ' + session.token };
  const [health, alerts] = await Promise.all([
    fetch('/api/workspaces/' + session.workspaceId + '/operations/health', { headers }).then(r => r.json()),
    fetch('/api/workspaces/' + session.workspaceId + '/operations/alerts', { headers }).then(r => r.json()),
  ]);
  const statuses = health.indicators.map(item => String(item.status).toLowerCase());
  const bad = statuses.some(status => ['red','critical','offline','failed','down','error'].includes(status));
  const warn = statuses.some(status => ['amber','warn','warning','yellow','degraded'].includes(status));
  return {
    alertTypes: alerts.alerts.length,
    expectedFooter: bad ? 'Service disruption detected' : warn ? 'Degraded performance' : 'All systems operational',
  };
})()`);

const routes = ["Home", "Ask", "Opportunities", "Strategy", "Content Department", "Producer", "Compliance", "Content", "Human Review", "Workforce", "Money", "Insights", "Audience", "Connections", "Settings"];
const missionTabs = ["Overview", "Timeline", "Live logs", "AI assistant", "Content"];

const results = [];
let index = 0;

// Exercise the real global-search input and backend before navigation.
const searchInputReady = await evaluate(`(() => {
  const input = document.querySelector('.topbar-search input[aria-label="Global search"]');
  if (!input) return false;
  input.focus();
  return true;
})()`);
if (searchInputReady) {
  await send("Input.insertText", { text: "Ops" }, sessionId);
  await sleep(800);
}
const searchResult = await evaluate(`(() => ({
  query: (document.querySelector('.topbar-search input[aria-label="Global search"]')||{}).value || '',
  rendered: !!document.querySelector('.search-results'),
  text: (document.querySelector('.search-results')||{}).innerText || '',
}))()`);
await evaluate(`(() => {
  const input = document.querySelector('.topbar-search input[aria-label="Global search"]');
  if (!input) return;
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(input, '');
  input.dispatchEvent(new Event('input', { bubbles: true }));
})()`);
for (const label of routes) {
  const clicked = await evaluate(`(() => {
    const nav = document.querySelector('nav[aria-label="Primary navigation"]');
    if (!nav) return false;
    const btn = [...nav.querySelectorAll('button')].find(b => {
      const text = b.innerText.trim();
      return text === ${JSON.stringify(label)} || text.startsWith(${JSON.stringify(label + "\n")});
    });
    if (!btn) return false;
    btn.click();
    return true;
  })()`);
  await sleep(1300);
  const rep = await report();
  await shot(`${String(index).padStart(2, "0")}-${label.replace(/\s+/g, "-").toLowerCase()}`);
  results.push({ label, clicked, ...rep });
  index++;

  if (label === "Connections") {
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
      results.push({ label: `Connections/${tab}`, ...trep });
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
await shot("89-mobile-home");
const mobileEditAvailable = await evaluate(`(() => {
  const button = [...document.querySelectorAll('button')]
    .find(item => /Edit setup/i.test(item.textContent || ''));
  if (button) button.click();
  return !!button;
})()`);
if (mobileEditAvailable) {
  await sleep(500);
  await shot("89-mobile-setup");
  const setupReport = await report();
  results.push({ label: "mobile-five-step-setup", ...setupReport });
}
await evaluate(`(() => { const b=[...document.querySelectorAll('button')].find(x=>/open navigation/i.test(x.getAttribute('aria-label')||'')); if(b)b.click(); return !!b; })()`);
await sleep(500);
await shot("90-mobile-nav-open");
const mrep = await report();
results.push({ label: "mobile-dashboard", ...mrep });

const mobileResults = [];
for (const label of ["Opportunities", "Strategy", "Content Department", "Producer", "Compliance", "Human Review", "Workforce", "Settings"]) {
  await evaluate(`(() => {
    const open = [...document.querySelectorAll('button')].find(x => /open navigation/i.test(x.getAttribute('aria-label') || ''));
    if (open) open.click();
  })()`);
  await sleep(100);
  await evaluate(`(() => {
    const nav = document.querySelector('nav[aria-label="Primary navigation"]');
    const btn = nav && [...nav.querySelectorAll('button')].find(b => {
      const text = b.innerText.trim();
      return text === ${JSON.stringify(label)} || text.startsWith(${JSON.stringify(label + "\n")});
    });
    if (btn) btn.click();
    return !!btn;
  })()`);
  await sleep(900);
  const mobileReport = await report();
  mobileResults.push({ label, ...mobileReport });
  await shot(`9${mobileResults.length}-${label.replace(/\s+/g, "-").toLowerCase()}`);
}

writeFileSync(`${OUT}/results.json`, JSON.stringify({ results, mobileResults, loginUx, launchObserved, searchResult, setupVerification, consoleProblems, uncaughtExceptions }, null, 2));
const crashes = results.filter((r) => r.crash || r.textLen === 0);
const accessibilityFailures = results.filter((r) => r.unlabeledControls > 0);
const mobileFailures = mobileResults.filter((r) => r.crash || r.textLen === 0 || r.horizontalOverflow || r.unlabeledControls > 0);
const footerFailures = results.filter((r) => r.footer !== backendTruth.expectedFooter);
const dashboardResult = results.find((r) => r.label === "Home");
const alertParityWorks = dashboardResult?.conditionRows === backendTruth.alertTypes;
const fourCirclesWork = dashboardResult?.financialCircles === 4 && dashboardResult?.unavailableFinancialMetrics === 4;
const bankrollWorks = dashboardResult?.bankrollHeading === "Bankroll" && dashboardResult?.homeIdentityCentered && dashboardResult?.bankrollCentered;
const researchResult = results.find((r) => r.label === "Opportunities");
const scoutTruthWorks = researchResult?.researchProviderNotConfigured && researchResult?.researchOpportunityEmpty;
const strategyResult = results.find((r) => r.label === "Strategy");
const strategistTruthWorks = strategyResult?.strategyProviderNotConfigured && strategyResult?.strategyBusinessContextIncomplete && strategyResult?.strategyBriefEmpty;
const contentDepartmentResult = results.find((r) => r.label === "Content Department");
const contentDepartmentTruthWorks = contentDepartmentResult?.contentProviderNotConfigured && contentDepartmentResult?.contentBusinessContextIncomplete && contentDepartmentResult?.contentPackageEmpty;
const producerResult = results.find((r) => r.label === "Producer");
const producerTruthWorks = producerResult?.productionProviderNotConfigured && producerResult?.productionJobEmpty;
const complianceResult = results.find((r) => r.label === "Compliance");
const complianceTruthWorks = complianceResult?.complianceProviderNotConfigured && complianceResult?.complianceEvidenceEmpty && complianceResult?.compliancePolicyFreshnessUnverified;
const mobileSetupResult = results.find((r) => r.label === "mobile-five-step-setup");
const mobileSetupWorks = !!mobileSetupResult && !mobileSetupResult.horizontalOverflow && mobileSetupResult.setupSmallTouchTargets === 0 && mobileSetupResult.businessManagerBrand;
console.log("ROUTES:", results.length);
console.log("BLANK/CRASH:", crashes.length);
console.log("SEARCH:", JSON.stringify(searchResult));
console.log("CONSOLE ERRORS/WARNINGS:", consoleProblems.length);
console.log("UNCAUGHT EXCEPTIONS:", uncaughtExceptions.length);
console.log("UNLABELED CONTROLS:", accessibilityFailures.length);
console.log("MOBILE SUPPLEMENTAL:", mobileResults.length, "failures:", mobileFailures.length);
console.log("BACKEND TRUTH:", JSON.stringify(backendTruth));
console.log("FOOTER MISMATCHES:", footerFailures.length);
console.log("ALERT ROW PARITY:", alertParityWorks);
console.log("FOUR-CIRCLE FINANCIAL HOME:", fourCirclesWork);
console.log("CENTERED HOME + BANKROLL:", bankrollWorks);
console.log("SCOUT TRUTHFUL NOT-CONFIGURED STATE:", scoutTruthWorks);
console.log("STRATEGIST TRUTHFUL NOT-CONFIGURED STATE:", strategistTruthWorks);
console.log("CONTENT DEPARTMENT TRUTHFUL NOT-CONFIGURED STATE:", contentDepartmentTruthWorks);
console.log("PRODUCER TRUTHFUL NOT-CONFIGURED STATE:", producerTruthWorks);
console.log("COMPLIANCE + CHIEF AUDITOR TRUTHFUL NOT-CONFIGURED STATE:", complianceTruthWorks);
console.log("MOBILE FIVE-STEP SETUP:", mobileSetupWorks);
for (const r of results) {
  console.log(`  ${r.crash ? "CRASH" : r.textLen === 0 ? "BLANK" : "ok   "} | ${r.label} | textLen=${r.textLen} | footer=${r.footer ?? "-"} | unlabeled=${r.unlabeledControls}`);
}
if (consoleProblems.length) console.log("CONSOLE DETAILS:", JSON.stringify(consoleProblems, null, 2));
if (uncaughtExceptions.length) console.log("EXCEPTION DETAILS:", JSON.stringify(uncaughtExceptions, null, 2));
const searchWorks = searchResult.query === "Ops" && searchResult.rendered;
const loginUxWorks = loginUx.signInHeading && !loginUx.loginWorkspaceField && loginUx.signupWorkspaceField;
process.exit(
  crashes.length === 0 &&
  accessibilityFailures.length === 0 &&
  mobileFailures.length === 0 &&
  footerFailures.length === 0 &&
  alertParityWorks &&
  fourCirclesWork &&
  bankrollWorks &&
  scoutTruthWorks &&
  strategistTruthWorks &&
  contentDepartmentTruthWorks &&
  producerTruthWorks &&
  complianceTruthWorks &&
  mobileSetupWorks &&
  consoleProblems.length === 0 &&
  uncaughtExceptions.length === 0 &&
  searchWorks &&
  loginUxWorks
    ? 0
    : 1,
);
