import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const root = process.cwd();
const baseUrl = "http://127.0.0.1:4173";
const entrypoints = ["/"];
const projectEntrypoints = [];

function collectHtml(directory) {
  if (!fs.existsSync(directory)) return;
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) collectHtml(full);
    else if (entry.isFile() && entry.name.toLowerCase() === "index.html") {
      const route = "/" + path.relative(root, full).split(path.sep).join("/");
      entrypoints.push(route);
      projectEntrypoints.push(route);
    }
  }
}

if (fs.existsSync(path.join(root, "arcade.html"))) entrypoints.push("/arcade.html");
collectHtml(path.join(root, "projects"));
if (projectEntrypoints.length === 0) {
  console.error("FAIL: no generated project entrypoints found; browser QA cannot pass.");
  process.exit(1);
}

const browser = await chromium.launch({ headless: true });
const failures = [];
const results = [];
try {
  for (const route of entrypoints) {
    for (const viewport of [
      { name: "desktop", width: 1365, height: 900 },
      { name: "mobile", width: 390, height: 844 }
    ]) {
      const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height } });
      await page.route("**/api/status", route => route.fulfill({
        status: 200, contentType: "application/json",
        body: JSON.stringify({ version: "browser-qa", gemini_configured: false, youtube_api_configured: false,
          youtube_channels_configured: 0, youtube_analytics_ready: false, openrouter_configured: false,
          jarvis: "online", nova: "online" })
      }));
      await page.route("**/api/team/status", route => route.fulfill({
        status: 200, contentType: "application/json",
        body: JSON.stringify({ status: "idle", task: "", phase: "Browser QA", active: [], completed: [] })
      }));
      const pageErrors = [];
      const localFailures = [];
      page.on("pageerror", error => pageErrors.push(error.message));
      page.on("response", response => {
        if (response.url().startsWith(baseUrl) && response.status() >= 400) localFailures.push(response.status() + " " + response.url());
      });
      try {
        const response = await page.goto(baseUrl + route, { waitUntil: "domcontentloaded", timeout: 20000 });
        if (!response || !response.ok()) localFailures.push("Document request did not return a successful response.");
        await page.locator("body").waitFor({ state: "visible", timeout: 5000 });
        await page.waitForTimeout(500);
        const bodyTextLength = await page.locator("body").innerText().then(value => value.trim().length).catch(() => 0);
        const visibleCanvas = await page.locator("canvas:visible").count();
        if (bodyTextLength === 0 && visibleCanvas === 0) localFailures.push("Page appears blank.");
        const dimensions = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth }));
        if (dimensions.document > dimensions.viewport + 2) localFailures.push("Horizontal overflow: " + dimensions.document + "px > " + dimensions.viewport + "px.");

        if (projectEntrypoints.includes(route)) {
          const html = fs.readFileSync(path.join(root, route.replace(/^\//, "")), "utf8");
          const scripts = [...html.matchAll(/<script\\b[^>]*src=["']([^"']+)["'][^>]*>/gi)].map(match => match[1]);
          for (const script of scripts) {
            if (/^(https?:)?\\/\\//i.test(script)) continue;
            const scriptPath = path.resolve(path.dirname(path.join(root, route.replace(/^\//, ""))), script.split(/[?#]/)[0]);
            if (!fs.existsSync(scriptPath)) localFailures.push("Missing project script: " + script);
          }
          if (await page.locator("canvas#wf-canvas").count()) {
            await page.locator("#wf-start-btn").click();
            await page.waitForFunction(() => document.querySelector("#wf-overlay")?.classList.contains("hidden"), null, { timeout: 3000 });
            const status = await page.locator("#wf-status").innerText();
            if (status !== "AKTIV") localFailures.push("Game did not enter active state after Start.");
            const canvasSize = await page.locator("#wf-canvas").evaluate(canvas => ({ width: canvas.width, height: canvas.height }));
            if (canvasSize.width < 1 || canvasSize.height < 1) localFailures.push("Game canvas has invalid dimensions.");
          }
        }
        const errors = [...pageErrors, ...localFailures];
        if (errors.length) failures.push(route + " [" + viewport.name + "]: " + errors.join(" | "));
        results.push({ route, viewport: viewport.name, status: errors.length ? "FAIL" : "PASS" });
      } catch (error) {
        failures.push(route + " [" + viewport.name + "]: " + error.message);
        results.push({ route, viewport: viewport.name, status: "FAIL" });
      } finally {
        await page.close();
      }
    }
  }
} finally {
  await browser.close();
}
for (const result of results) console.log(result.status + " " + result.route + " (" + result.viewport + ")");
console.log("\\nJARVIS QA: " + results.filter(item => item.status === "PASS").length + "/" + results.length + " viewport checks passed across " + entrypoints.length + " page(s).");
if (failures.length) {
  console.error("\\nFailures:");
  for (const failure of failures) console.error("- " + failure);
  process.exit(1);
}
