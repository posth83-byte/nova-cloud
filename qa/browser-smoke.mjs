import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const root = process.cwd();
const baseUrl = "http://127.0.0.1:4173";
const entrypoints = ["/"];

function collectHtml(directory) {
  if (!fs.existsSync(directory)) return;
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) collectHtml(full);
    else if (entry.isFile() && entry.name.toLowerCase() === "index.html") {
      entrypoints.push("/" + path.relative(root, full).split(path.sep).join("/"));
    }
  }
}

if (fs.existsSync(path.join(root, "arcade.html"))) entrypoints.push("/arcade.html");
collectHtml(path.join(root, "projects"));

if (entrypoints.length === 0) {
  console.log("No browser project entrypoints found; nothing to smoke-test.");
  process.exit(0);
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

      // The preview server is static HTML; provide deterministic local API fixtures
      // so dashboard smoke tests validate the UI rather than requiring live secrets.
      await page.route("**/api/status", route => route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          version: "browser-qa",
          gemini_configured: false,
          youtube_api_configured: false,
          youtube_channels_configured: 0,
          youtube_analytics_ready: false,
          openrouter_configured: false,
          jarvis: "online",
          nova: "online"
        })
      }));
      await page.route("**/api/team/status", route => route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "idle",
          task: "",
          phase: "Browser QA",
          active: [],
          completed: []
        })
      }));
      const pageErrors = [];
      const localFailures = [];

      page.on("pageerror", error => pageErrors.push(error.message));
      page.on("response", response => {
        const url = response.url();
        if (url.startsWith(baseUrl) && response.status() >= 400) {
          localFailures.push(`${response.status()} ${url}`);
        }
      });

      try {
        const response = await page.goto(baseUrl + route, {
          waitUntil: "domcontentloaded",
          timeout: 20000
        });
        if (!response || !response.ok()) {
          localFailures.push("Document request did not return a successful response.");
        }
        await page.locator("body").waitFor({ state: "visible", timeout: 5000 });
        await page.waitForTimeout(700);

        const bodyTextLength = await page.locator("body").innerText().then(text => text.trim().length).catch(() => 0);
        const hasVisibleCanvas = await page.locator("canvas:visible").count().then(count => count > 0);
        if (bodyTextLength === 0 && !hasVisibleCanvas) {
          localFailures.push("Page appears blank (no visible text or canvas).");
        }

        const dimensions = await page.evaluate(() => ({
          viewport: document.documentElement.clientWidth,
          document: document.documentElement.scrollWidth
        }));
        if (dimensions.document > dimensions.viewport + 2) {
          localFailures.push(`Horizontal overflow: document ${dimensions.document}px, viewport ${dimensions.viewport}px.`);
        }

        const errors = [...pageErrors, ...localFailures];
        if (errors.length) {
          failures.push(`${route} [${viewport.name}]: ${errors.join(" | ")}`);
        }
        results.push({ route, viewport: viewport.name, status: errors.length ? "FAIL" : "PASS" });
      } catch (error) {
        failures.push(`${route} [${viewport.name}]: ${error.message}`);
        results.push({ route, viewport: viewport.name, status: "FAIL" });
      } finally {
        await page.close();
      }
    }
  }
} finally {
  await browser.close();
}

for (const result of results) {
  console.log(`${result.status} ${result.route} (${result.viewport})`);
}

console.log(`\nJARVIS QA: ${results.filter(item => item.status === "PASS").length}/${results.length} viewport checks passed across ${entrypoints.length} page(s).`);

if (failures.length) {
  console.error("\nFailures:");
  for (const failure of failures) console.error("- " + failure);
  process.exit(1);
}
