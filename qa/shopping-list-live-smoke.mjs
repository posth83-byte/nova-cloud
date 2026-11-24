import { chromium } from "playwright";

const siteUrl = (process.env.SHOPPING_LIST_BASE_URL || "").replace(/\/$/, "");
const apiUrl = (process.env.SHOPPING_LIST_API_URL || "").replace(/\/$/, "");
if (!siteUrl.startsWith("https://") || !apiUrl.startsWith("https://")) {
  throw new Error("Live shopping-list QA requires HTTPS site and API URLs.");
}

const browser = await chromium.launch({ headless: true });
const ownerContext = await browser.newContext({
  viewport: { width: 390, height: 844 },
  serviceWorkers: "block"
});
const partnerContext = await browser.newContext({
  viewport: { width: 390, height: 844 },
  serviceWorkers: "block"
});
const failures = [];
const requests = [];
const responses = [];
let token = "";
let owner;
let partner;

function watch(page, label) {
  page.on("pageerror", error => failures.push(label + " page error: " + error.message));
  page.on("requestfailed", request => {
    if (request.url().startsWith(apiUrl)) {
      failures.push(label + " API request failed: " + request.method() + " " + request.url() + " " + (request.failure()?.errorText || ""));
    }
  });
  page.on("request", request => {
    if (request.url().startsWith(apiUrl)) {
      requests.push({ label, method: request.method(), url: request.url() });
    }
  });
  page.on("response", response => {
    if (response.url().startsWith(apiUrl)) {
      const entry = { label, method: response.request().method(), url: response.url(), status: response.status() };
      responses.push(entry);
      if (response.status() >= 400) failures.push(label + " API returned " + response.status() + ": " + response.url());
    }
  });
}

try {
  await ownerContext.addInitScript(() => {
    Object.defineProperty(navigator, "share", {
      configurable: true,
      value: async data => { window.__sharedPayload = data; }
    });
  });

  owner = await ownerContext.newPage();
  watch(owner, "owner");
  const home = await owner.goto(siteUrl + "/", { waitUntil: "domcontentloaded", timeout: 30000 });
  if (!home?.ok()) throw new Error("Shopping-list home page did not return HTTP success.");
  await owner.locator("#itemInput").waitFor({ state: "visible", timeout: 10000 });

  const firstItem = "JARVIS-QA-Mjölk-" + Date.now();
  const secondItem = "JARVIS-QA-Bröd-" + Date.now();
  await owner.locator("#itemInput").fill(firstItem);
  await owner.locator('#addForm button[type="submit"]').click();
  await owner.waitForFunction(name => document.querySelector("#list")?.innerText.includes(name), firstItem, { timeout: 5000 });

  await owner.locator("#share").click();
  await owner.waitForFunction(() => !!window.__sharedPayload?.url, null, { timeout: 15000 });
  const shareUrl = await owner.evaluate(() => window.__sharedPayload.url);
  const parsedShareUrl = new URL(shareUrl);
  const tokenMatch = parsedShareUrl.hash.match(/(?:^|&)list=([^&]+)/);
  if (!tokenMatch) throw new Error("Share link did not contain the shared-list token.");
  token = decodeURIComponent(tokenMatch[1]);
  if (await owner.evaluate(() => localStorage.getItem("shoppingListToken")) !== token) {
    throw new Error("Owner did not persist the shared-list token.");
  }

  partner = await partnerContext.newPage();
  watch(partner, "partner");
  const partnerHome = await partner.goto(shareUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
  if (!partnerHome?.ok()) throw new Error("Partner device could not open the shared link.");
  await partner.waitForFunction(name => document.querySelector("#list")?.innerText.includes(name), firstItem, { timeout: 15000 });
  if (await partner.evaluate(() => localStorage.getItem("shoppingListToken")) !== token) {
    throw new Error("Partner device did not persist the shared-list token.");
  }

  const firstRow = partner.locator("#list article.item").filter({ hasText: firstItem });
  await firstRow.locator("[data-check]").click();
  await partner.waitForFunction(name => {
    const row = [...document.querySelectorAll("#list article.item")].find(item => item.innerText.includes(name));
    return row?.classList.contains("done");
  }, firstItem, { timeout: 10000 });

  await owner.bringToFront();
  await owner.waitForFunction(name => {
    const row = [...document.querySelectorAll("#list article.item")].find(item => item.innerText.includes(name));
    return row?.classList.contains("done");
  }, firstItem, { timeout: 15000 });

  await owner.locator("#itemInput").fill(secondItem);
  await owner.locator('#addForm button[type="submit"]').click();
  await owner.waitForFunction(name => document.querySelector("#list")?.innerText.includes(name), secondItem, { timeout: 8000 });
  await partner.bringToFront();
  await partner.waitForFunction(name => document.querySelector("#list")?.innerText.includes(name), secondItem, { timeout: 15000 });

  const secondRow = partner.locator("#list article.item").filter({ hasText: secondItem });
  await secondRow.locator("[data-del]").click();
  await partner.waitForFunction(name => !document.querySelector("#list")?.innerText.includes(name), secondItem, { timeout: 8000 });
  await owner.bringToFront();
  await owner.waitForFunction(name => !document.querySelector("#list")?.innerText.includes(name), secondItem, { timeout: 15000 });

  await owner.locator("#clear").click();
  await owner.waitForFunction(name => !document.querySelector("#list")?.innerText.includes(name), firstItem, { timeout: 8000 });
  await partner.bringToFront();
  await partner.waitForFunction(name => !document.querySelector("#list")?.innerText.includes(name), firstItem, { timeout: 15000 });

  const expected = [
    ["POST", "/api/shopping-list"],
    ["GET", "/api/shopping-list"],
    ["POST", "/api/shopping-list/items"],
    ["PATCH", "/api/shopping-list/items/"],
    ["DELETE", "/api/shopping-list/items/"],
    ["POST", "/api/shopping-list/clear-completed"]
  ];
  for (const [method, path] of expected) {
    if (!responses.some(entry => entry.method === method && new URL(entry.url).pathname.startsWith(path))) {
      failures.push("Expected live API operation was not observed: " + method + " " + path);
    }
  }

  if (failures.length) throw new Error(failures.join("\n"));
  console.log("PASS live shared shopping list: create, share, second-device open, cross-device check-off, add, delete, clear-completed.");
  console.log("PASS live API operations: " + responses.map(item => item.method + " " + new URL(item.url).pathname + " " + item.status).join(" | "));
} finally {
  if (token) {
    try {
      const auth = { Authorization: "Bearer " + token };
      const listResponse = await ownerContext.request.get(apiUrl + "/api/shopping-list", { headers: auth, timeout: 10000 });
      if (listResponse.ok()) {
        const list = await listResponse.json();
        for (const item of list.items || []) {
          await ownerContext.request.delete(apiUrl + "/api/shopping-list/items/" + encodeURIComponent(item.id), { headers: auth, timeout: 10000 });
        }
      }
    } catch (error) {
      console.log("WARN live QA cleanup: " + error.message);
    }
  }
  await ownerContext.close();
  await partnerContext.close();
  await browser.close();
}
