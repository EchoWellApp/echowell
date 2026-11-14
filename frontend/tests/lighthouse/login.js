// Scripted admin login for Lighthouse CI (TRD 13 TST-125, TRD 16 CIC-116, FEAT-079-FR-10).
// Referenced by frontend/lighthouserc.json (`collect.puppeteerScript`); LHCI calls it before each URL.
//
// The dashboard keeps its token in sessionStorage["echowell.auth"] (TRD 04 FE-050), which is per tab,
// and Lighthouse audits each URL in a new tab. So the script logs in once through the real form on
// /login, reads the stored session and installs it in every page the browser opens afterwards
// (evaluateOnNewDocument), before the page's own scripts run. No credential is written to disk or logs.
//
// Environment: LHCI_BASE_URL (default http://localhost:3001), LHCI_ADMIN_EMAIL (default the seeded
// admin@example.com), LHCI_ADMIN_PASSWORD or SEED_ADMIN_PASSWORD (the per-job masked value, CIC-034).
const KEY = "echowell.auth";
const state = new WeakMap();

module.exports = async (browser) => {
  if (state.has(browser)) return;
  const base = process.env.LHCI_BASE_URL || "http://localhost:3001";
  const email = process.env.LHCI_ADMIN_EMAIL || "admin@example.com";
  const password = process.env.LHCI_ADMIN_PASSWORD || process.env.SEED_ADMIN_PASSWORD;
  if (!password)
    throw new Error("Set LHCI_ADMIN_PASSWORD or SEED_ADMIN_PASSWORD for the scripted login");

  const page = await browser.newPage();
  await page.goto(`${base}/login`, { waitUntil: "networkidle0" });
  await page.type("#login-email", email);
  await page.type("#login-password", password);
  await Promise.all([
    page.waitForFunction((k) => window.sessionStorage.getItem(k) !== null, { timeout: 30000 }, KEY),
    page.click('button[type="submit"]'),
  ]);
  const stored = await page.evaluate((k) => window.sessionStorage.getItem(k), KEY);
  await page.close();

  const install = async (target) => {
    const opened = await target.page().catch(() => null);
    if (opened) {
      await opened.evaluateOnNewDocument(
        (k, value) => window.sessionStorage.setItem(k, value),
        KEY,
        stored,
      );
    }
  };
  for (const target of browser.targets()) await install(target);
  browser.on("targetcreated", install);
  state.set(browser, stored);
};
