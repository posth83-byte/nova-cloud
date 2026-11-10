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
        const isExpectedRetry = response.url() === baseUrl + "/api/video/team/jobs/abcdef123456" && response.status() === 503;
        if (!isExpectedRetry && response.url().startsWith(baseUrl) && response.status() >= 400) {
          localFailures.push(response.status() + " " + response.url());
        }
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
          const scripts = [...html.matchAll(/<script\b[^>]*src=["']([^"']+)["'][^>]*>/gi)].map(match => match[1]);
          for (const script of scripts) {
            if (/^(https?:)?\/\//i.test(script)) continue;
            const scriptPath = path.resolve(path.dirname(path.join(root, route.replace(/^\//, ""))), script.split(/[?#]/)[0]);
            if (!fs.existsSync(scriptPath)) localFailures.push("Missing project script: " + script);
          }
          if (route.includes("/projects/nexora-store/")) {
            await page.waitForFunction(() => document.querySelectorAll("#productGrid .product-card").length === 6, null, { timeout: 7000 });
            const imageResults = await page.locator("#productGrid .product-image").evaluateAll(images => Promise.all(images.map(img => {
              img.loading = "eager";
              return img.decode().then(() => ({ src: img.currentSrc || img.src, ok: img.naturalWidth > 0 })).catch(() => ({ src: img.src, ok: false }));
            })));
            for (const image of imageResults) if (!image.ok) localFailures.push("Product image failed to load: " + image.src);
            await page.locator('[data-category="belysning"]').click();
            if (await page.locator("#productGrid .product-card").count() !== 1) localFailures.push("Category filter did not return the expected product.");
            await page.locator('[data-category="alla"]').click();
            await page.locator("#searchInput").fill("ullpläd");
            if (await page.locator("#productGrid .product-card").count() !== 1) localFailures.push("Product search did not return the expected result.");
            await page.locator("#searchInput").fill("");
            await page.locator('[data-add="lamp"]').click();
            if ((await page.locator("#cartCount").innerText()) !== "1") localFailures.push("Add-to-cart did not update the cart count.");
            await page.locator("#cartOpen").click();
            if (!(await page.locator("#cartDrawer").evaluate(el => el.classList.contains("open")))) localFailures.push("Cart drawer did not open.");
            await page.locator('[data-quantity="1"]').click();
            if (!(await page.locator("#cartLines").innerText()).includes("2")) localFailures.push("Cart quantity control did not increment.");
            await page.locator("#checkoutOpen").click();
            if (!(await page.locator("#checkoutBackdrop").evaluate(el => el.classList.contains("open")))) localFailures.push("Checkout test modal did not open.");
            await page.locator('#checkoutForm input[name="name"]').fill("Testkund");
            await page.locator('#checkoutForm input[name="email"]').fill("test@example.com");
            await page.locator('#checkoutForm input[name="address"]').fill("Testgatan 1");
            await page.locator('#checkoutForm input[name="postal"]').fill("12345");
            await page.locator('#checkoutForm input[name="city"]').fill("Stockholm");
            await page.locator('#checkoutForm button[type="submit"]').click();
            if (await page.locator("#checkoutSuccess").isHidden()) localFailures.push("Checkout did not show the test-order confirmation.");
            if ((await page.locator("#cartCount").innerText()) !== "0") localFailures.push("Cart was not cleared after the test order.");
          }
          if (route.includes("jarvis-kritisk-slutgranskning-av-pr-26-o")) {
            // Functional checks for the generated JARVIS portal, not just page-load smoke tests.
            await page.locator("#taskInput").fill("QA funktionstest");
            await page.locator("#addTaskBtn").click();
            if (await page.locator("#taskList").getByText("QA funktionstest").count() !== 1) localFailures.push("Task add did not create a visible task.");
            await page.locator("#taskList").getByRole("button", { name: "Klar" }).last().click();
            if (await page.locator("#taskList").getByText("QA funktionstest").count() !== 0) localFailures.push("Task completion did not remove the task.");

            if (viewport.name === "mobile") {
              await page.locator("#menuToggle").click();
              if (!(await page.locator("#mainNav").evaluate(el => el.classList.contains("open")))) localFailures.push("Mobile menu did not open.");
            }
            await page.locator('[data-target="panel-game"]').click();
            await page.waitForFunction(() => { const panel = document.querySelector("#panel-game"); const canvas = document.querySelector("#gameCanvas"); const container = document.querySelector("#game-container"); return panel?.classList.contains("active") && canvas && canvas.width >= 280 && container?.clientWidth > 0; }, null, { timeout: 5000 });
            await page.locator("#startGameBtn").click();
            if ((await page.locator("#gameOverlay").evaluate(el => getComputedStyle(el).display)) !== "none") localFailures.push("Game overlay did not close after Start.");
            const beforeX = await page.evaluate(() => window.__jarvisGame?.player.x);
            if (viewport.name === "mobile") {
              await page.locator("#btnRight").dispatchEvent("pointerdown", { pointerId: 1, pointerType: "touch", isPrimary: true });
              await page.waitForTimeout(160);
              await page.locator("#btnRight").dispatchEvent("pointerup", { pointerId: 1, pointerType: "touch", isPrimary: true });
            } else {
              await page.keyboard.down("ArrowRight");
              await page.waitForTimeout(160);
              await page.keyboard.up("ArrowRight");
            }
            const afterX = await page.evaluate(() => window.__jarvisGame?.player.x);
            const gameRunning = await page.evaluate(() => window.__jarvisGame?.isRunning);
            if (gameRunning !== true) localFailures.push("Game is not running after Start.");
            if (!(afterX > beforeX)) localFailures.push("Right movement control did not move the player.");

            if (viewport.name === "mobile") {
              await page.locator("#menuToggle").click();
              if (!(await page.locator("#mainNav").evaluate(el => el.classList.contains("open")))) localFailures.push("Mobile menu did not reopen before Diagnostics navigation.");
            }
            await page.locator('[data-target="panel-diag"]').click();
            await page.route("**/health", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "online" }) }));
            await page.route("**/api/status", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ gemini_configured: true }) }));
            await page.route("**/api/chat", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "online", engine: "Gemini", reply: "OK" }) }));
            await page.route("**/api/memory/status", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "online", storage: "supabase" }) }));
            await page.locator("#runDiagBtn").click();
            await page.waitForFunction(() => document.querySelector("#status-gemini")?.textContent.includes("Gemini-anrop lyckades"), null, { timeout: 5000 });
            await page.waitForFunction(() => document.querySelector("#status-supabase")?.textContent.includes("Supabase används"), null, { timeout: 5000 });
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
        if (route === "/") {
          // Navigate through the real home-screen control instead of force-opening the studio.
          await page.locator(".jarvis-nova-link").click();
          await page.waitForFunction(() => !document.querySelector("#novaView")?.classList.contains("hidden"), null, { timeout: 5000 });
          if (await page.locator("#videoTeamCreator").count() !== 1) localFailures.push("Video creator panel is missing.");
          if (await page.locator("#videoFindIdeas").count() !== 1) localFailures.push("Trend discovery button is missing.");
          if (await page.locator("#videoCreateOriginal").count() !== 1) localFailures.push("Original video button is missing.");
          if (await page.locator("#videoAspectSelect").count() !== 1) localFailures.push("Video aspect selector is missing.");
          if (await page.locator("#videoDurationSelect").count() !== 1) localFailures.push("Factual video duration selector is missing.");
          await page.locator("#videoTypeSelect").selectOption("explainer");
          if (await page.locator("#videoDurationWrap").evaluate(el => getComputedStyle(el).display) === "none") localFailures.push("Factual duration selector did not appear for explainers.");
          await page.locator("#videoTypeSelect").selectOption("humor");
          if (await page.locator("#videoDurationWrap").evaluate(el => getComputedStyle(el).display) !== "none") localFailures.push("Factual duration selector remained visible for humor.");

          await page.route("**/api/video/team/ideas", route => route.fulfill({
            status: 200, contentType: "application/json",
            body: JSON.stringify({ status: "ok", ideas: [{ title: "Testtrend Sverige", traffic: "20K+", source: "Google Trends Sverige", source_url: "https://trends.google.com/", angle: "Gör en egen version." }], note: "Testdata." })
          }));
          await page.locator("#videoFindIdeas").click({ force: true });
          await page.waitForFunction(() => document.querySelector("#videoIdeasList")?.innerText.includes("Testtrend Sverige"), null, { timeout: 5000 });
          if (!(await page.locator("#videoIdeasList").innerText()).includes("SKAPA EGEN VIDEO")) localFailures.push("Trend result does not offer an original-video action.");

          let createCount = 0;
          await page.route("**/api/video/team/create", async route => {
            createCount++;
            const jobId = createCount === 1 ? "abcdef123456" : "failed123456";
            await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
              status: "queued", job_id: jobId, status_url: "/api/video/team/jobs/" + jobId, topic: "QA humor"
            }) });
          });
          let statusCount = 0;
          await page.route("**/api/video/team/jobs/abcdef123456", async route => {
            statusCount++;
            if (statusCount === 1) return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Tillfälligt servicefel" }) });
            const state = statusCount === 2 ? "queued" : statusCount === 3 ? "running" : "completed";
            const body = state === "completed" ? { status: state, result: {
              status: "completed", job_id: "abcdef123456", topic: "QA humor", format: "9:16", resolution: "720x1280",
              storage_status: "persistent", visual_source: "Egen grafik", script: [{ heading: "TEST", line: "En testscen.", punchline: "Testpoäng." }],
              video_url: "/api/video/team/created/abcdef123456", subtitles_url: "/api/video/team/subtitles/abcdef123456"
            }} : { status: state, job_id: "abcdef123456" };
            return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
          });
          const mp4Bytes = Buffer.from([0,0,0,24,102,116,121,112,105,115,111,109,0,0,2,0,105,115,111,109,105,115,111,50]);
          await page.route("**/api/video/team/created/*", route => route.fulfill({ status: 200, contentType: "video/mp4", body: mp4Bytes }));
          await page.route("**/api/video/team/subtitles/*", route => route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", body: "1\\n00:00:00,000 --> 00:00:02,000\\nTestundertext\\n" }));
          await page.evaluate(() => {
            const originalTimeout = window.setTimeout.bind(window);
            window.setTimeout = (callback, delay, ...args) => originalTimeout(callback, delay === 2500 || delay === 1000 || delay === 2000 || delay === 4000 ? 5 : delay, ...args);
          });
          await page.locator("#videoOriginalTopic").fill("QA humor");
          await page.locator("#videoCreateOriginal").click();
          await page.waitForFunction(() => document.querySelector("#videoCreatorResult a")?.textContent.includes("FÄRDIG MP4"), null, { timeout: 8000 });
          if (statusCount < 4) localFailures.push("Queued/running/completed status sequence was not fully polled after a transient 503.");
          if (!(await page.locator("#videoCreatorResult video").count())) localFailures.push("Created-video preview element is missing.");
          if (!(await page.locator("#videoCreatorResult").innerText()).includes("TEST")) localFailures.push("Created-video script was not displayed.");
          const exportLinks = page.locator("#videoCreatorResult a");
          const mp4Href = await exportLinks.filter({ hasText: "FÄRDIG MP4" }).getAttribute("href");
          const srtHref = await exportLinks.filter({ hasText: "UNDERtexter" }).getAttribute("href");
          if (!mp4Href || !srtHref) localFailures.push("MP4 or SRT download link is missing.");
          else {
            // Use the page's browser context so these requests pass through page.route mocks.
            const exportResults = await page.evaluate(async ([mp4Url, srtUrl]) => {
              const [mp4Response, srtResponse] = await Promise.all([fetch(mp4Url), fetch(srtUrl)]);
              const mp4 = await mp4Response.arrayBuffer();
              const srt = await srtResponse.text();
              return {
                mp4Ok: mp4Response.ok && (mp4Response.headers.get("content-type") || "").includes("video/mp4") && mp4.byteLength >= 16,
                srtOk: srtResponse.ok && srt.includes("Testundertext")
              };
            }, [mp4Href, srtHref]);
            if (!exportResults.mp4Ok) localFailures.push("MP4 export endpoint did not return video content.");
            if (!exportResults.srtOk) localFailures.push("SRT export endpoint did not return subtitle content.");
          }
          // A failed background job must produce a visible, actionable error state.
          await page.route("**/api/video/team/jobs/failed123456", route => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "failed", error: "Simulerat renderingsfel" }) }));
          await page.locator("#videoCreateOriginal").click();
          await page.waitForFunction(() => document.querySelector("#videoCreatorStatus")?.textContent.includes("Simulerat renderingsfel"), null, { timeout: 8000 });
          if (!(await page.locator("#videoCreatorStatus").evaluate(el => el.classList.contains("error")))) localFailures.push("Failed job did not display an error state.");

           // JARVIS chat must start the real video queue and show the finished MP4 in the same chat bubble.
           let jarvisChatApiCalled = false;
           await page.route("**/api/chat", async route => {
             if ((route.request().postData() || "").includes("JARVIS CHAT BRIDGE TEST")) {
               jarvisChatApiCalled = true;
               return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "online", reply: "Unexpected generic chat response." }) });
             }
             return route.fallback();
           });
           await page.route("**/api/video/team/create", async route => {
             if ((route.request().postData() || "").includes("JARVIS CHAT BRIDGE TEST")) {
               return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
                 status: "queued", job_id: "jarvis123456", status_url: "/api/video/team/jobs/jarvis123456"
               }) });
             }
             return route.fallback();
           });
           await page.route("**/api/video/team/jobs/jarvis123456", route => route.fulfill({
             status: 200, contentType: "application/json",
             body: JSON.stringify({ status: "completed", job_id: "jarvis123456", result: {
               status: "completed", job_id: "jarvis123456", topic: "JARVIS CHAT BRIDGE TEST", format: "9:16",
               resolution: "540x960", storage_status: "persistent", video_url: "/api/video/team/created/jarvis123456",
               subtitles_url: "/api/video/team/subtitles/jarvis123456", script: [{ heading: "TEST", line: "Direktleverans från JARVIS." }]
             } })
           }));
           await page.route("**/api/video/team/created/jarvis123456", route => route.fulfill({
             status: 200, contentType: "video/mp4", body: mp4Bytes
           }));
           await page.route("**/api/video/team/subtitles/jarvis123456", route => route.fulfill({
             status: 200, contentType: "text/plain; charset=utf-8", body: "1\\n00:00:00,000 --> 00:00:02,000\\nJARVIS test\\n"
           }));
           await page.locator(".room-topbar .back-btn").first().click();
           await page.waitForFunction(() => !document.querySelector("#novaView")?.classList.contains("hidden"), null, { timeout: 5000 }).catch(() => {});
           await page.locator("#jarvisInput").fill("Skapa en kort video om JARVIS CHAT BRIDGE TEST");
           await page.locator("#jarvisSend").click();
           await page.waitForFunction(() => {
             const bubble = [...document.querySelectorAll("#jarvisMessages .msg.ai")].find(node => node.querySelector('a[href*="jarvis123456"]'));
             return !!bubble && !!bubble.querySelector("video");
           }, null, { timeout: 8000 });
           if (jarvisChatApiCalled) localFailures.push("JARVIS video request incorrectly went through the generic /api/chat route.");
           const jarvisVideoBubble = page.locator("#jarvisMessages .msg.ai").filter({ has: page.locator('a[href*="jarvis123456"]') }).first();
           if (!(await jarvisVideoBubble.innerText()).includes("Din video är färdig")) localFailures.push("JARVIS chat did not display the completed-video confirmation.");
           if (!(await jarvisVideoBubble.locator("a").count())) localFailures.push("JARVIS chat did not include an MP4 delivery link.");
           if (!(await jarvisVideoBubble.locator("video").count())) localFailures.push("JARVIS chat did not include an inline MP4 preview.");

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
console.log("\nJARVIS QA: " + results.filter(item => item.status === "PASS").length + "/" + results.length + " viewport checks passed across " + entrypoints.length + " page(s).");
if (failures.length) {
  console.error("\nFailures:");
  for (const failure of failures) console.error("- " + failure);
  process.exit(1);
}
