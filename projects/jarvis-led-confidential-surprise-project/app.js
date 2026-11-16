(() => {
  "use strict";

  const STORAGE_KEY = "kampanjstudio-draft-v1";
  const form = document.getElementById("campaignForm");
  const formStatus = document.getElementById("formStatus");
  const resultCards = document.getElementById("resultCards");
  const resultsContent = document.getElementById("resultsContent");
  const emptyState = document.getElementById("emptyState");
  let currentCards = [];

  const byId = (id) => document.getElementById(id);
  const value = (id) => byId(id).value.trim();

  function getFormData() {
    return {
      businessName: value("businessName"),
      businessType: value("businessType"),
      location: value("location"),
      audience: value("audience") || "personer i närområdet",
      offer: value("offer"),
      tone: value("tone"),
      goal: value("goal"),
      cta: value("cta") || defaultCta(value("goal")),
      channels: [...form.querySelectorAll('input[name="channels"]:checked')].map((item) => item.value)
    };
  }

  function defaultCta(goal) {
    const labels = {
      visits: "Besök oss i dag",
      bookings: "Boka din tid",
      sales: "Se erbjudandet",
      leads: "Hör av dig för mer information"
    };
    return labels[goal] || "Hör av dig";
  }

  function saveDraft() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(getFormData()));
      formStatus.textContent = "Utkast sparat på den här enheten.";
    } catch (error) {
      formStatus.textContent = "Webbläsaren kunde inte spara utkastet. Du kan ändå skapa och exportera.";
    }
  }

  function restoreDraft() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      if (!saved) return;
      ["businessName", "businessType", "location", "audience", "offer", "tone", "goal", "cta"].forEach((key) => {
        if (typeof saved[key] === "string" && byId(key)) byId(key).value = saved[key];
      });
      form.querySelectorAll('input[name="channels"]').forEach((item) => {
        item.checked = Array.isArray(saved.channels) ? saved.channels.includes(item.value) : false;
      });
      formStatus.textContent = "Ditt senaste utkast har hämtats från den här enheten.";
    } catch (error) {
      formStatus.textContent = "Ett tidigare utkast kunde inte läsas.";
    }
  }

  function opening(tone, audience) {
    const options = {
      warm: "Hej " + audience + "! Vi vill gärna tipsa dig om något från vår verksamhet.",
      professional: "Ett genomtänkt val för " + audience + ".",
      playful: "Dags för något nytt? Vi har ett tips till " + audience + "!",
      premium: "För " + audience + " som uppskattar omtanke och kvalitet."
    };
    return options[tone] || options.warm;
  }

  function businessLabel(type) {
    const labels = {
      butik: "butik",
      cafe: "café eller restaurang",
      salon: "salong",
      service: "tjänsteföretag",
      craft: "hantverksföretag",
      consultant: "konsultverksamhet",
      other: "verksamhet"
    };
    return labels[type] || "verksamhet";
  }

  function buildCards(data) {
    const name = data.businessName;
    const area = data.location ? " i " + data.location : "";
    const audience = data.audience;
    const offer = data.offer.replace(/[.!?]+$/, "");
    const cta = data.cta.replace(/[.!?]+$/, "");
    const hello = opening(data.tone, audience);
    const channelText = data.channels.length ? data.channels.join(", ") : "valfri kanal";
    const goalText = {
      visits: "fler besök",
      bookings: "fler bokningar",
      sales: "ökad försäljning",
      leads: "fler förfrågningar"
    }[data.goal] || "mer synlighet";

    const posts = [
      {
        title: "Inlägg 1 · Lyft erbjudandet",
        tag: "Sociala medier",
        body: hello + "\n\nHos " + name + " vill vi göra det enkelt att upptäcka vad som passar dig. Just nu lyfter vi fram: " + offer + ".\n\n" + cta + (area ? " – vi finns" + area + "." : ".")
      },
      {
        title: "Inlägg 2 · Behov och lösning",
        tag: "Sociala medier",
        body: "Letar du efter en " + businessLabel(data.businessType) + area + "? " + name + " hjälper dig att komma vidare med ett tydligt och personligt bemötande.\n\n" + offer + ".\n\nSpara inlägget eller skicka det till någon som kan ha nytta av det. " + cta + "."
      },
      {
        title: "Inlägg 3 · Påminnelse",
        tag: "Sociala medier",
        body: "En liten påminnelse från " + name + ": " + offer + ".\n\nKanske är det precis det du har letat efter? Vi välkomnar " + audience + " att ta nästa steg.\n\n" + cta + "."
      }
    ];

    const ads = [
      {
        title: "Annons 1 · Tydligt erbjudande",
        tag: "Annons",
        body: name + area + "\n" + offer + ".\nFör " + audience + " som vill ha ett enkelt nästa steg.\n" + cta + "."
      },
      {
        title: "Annons 2 · Nyfikenhet",
        tag: "Annons",
        body: "Har du upptäckt " + name + "?\nVi är en " + businessLabel(data.businessType) + area + " och vill gärna visa dig: " + offer + ".\nTa en titt och se om det passar dig. " + cta + "."
      }
    ];

    const stories = [
      { title: "Story 1 · Fånga intresset", tag: "Story", body: "Behöver du något nytt?\n" + name + area + "\n" + hello },
      { title: "Story 2 · Visa erbjudandet", tag: "Story", body: "Just nu vill vi lyfta:\n" + offer + "\nEnkelt, tydligt och nära dig." },
      { title: "Story 3 · Uppmana till handling", tag: "Story", body: "Redo att ta nästa steg?\n" + cta + "\nSkriv till oss eller besök oss." }
    ];

    const schedule = [
      "Måndag – Publicera inlägg 1 och presentera erbjudandet.",
      "Tisdag – Dela Story 1 och bjud in till frågor.",
      "Onsdag – Publicera inlägg 2 med fokus på kundens behov.",
      "Torsdag – Dela Story 2 och påminn om erbjudandet.",
      "Fredag – Testa annons 1 med en tydlig uppmaning.",
      "Lördag – Publicera inlägg 3 eller dela en aktuell bild från verksamheten.",
      "Söndag – Dela Story 3 och planera nästa veckas innehåll."
    ].join("\n");

    const hashtags = [
      "#" + name.toLowerCase().replace(/[^a-zåäö0-9]+/g, ""),
      "#" + businessLabel(data.businessType).toLowerCase().replace(/[^a-zåäö0-9]+/g, ""),
      data.location ? "#" + data.location.toLowerCase().replace(/[^a-zåäö0-9]+/g, "") : "",
      "#lokaltföretag",
      "#svensktföretag"
    ].filter(Boolean).join(" ");

    return [
      { title: "Kampanjens riktning", tag: "Översikt", wide: true, body: "Verksamhet: " + name + " – " + businessLabel(data.businessType) + area + "\nMål: " + goalText + "\nMålgrupp: " + audience + "\nKanaler: " + channelText + "\n\nKärnbudskap: " + offer + ".\nTon: " + toneLabel(data.tone) + ". Anpassa formuleringarna så att de stämmer med ditt varumärke." },
      ...posts,
      ...ads,
      ...stories,
      { title: "Publiceringsplan · 7 dagar", tag: "Plan", wide: true, body: schedule },
      { title: "Hashtagförslag", tag: "Upptäckbarhet", wide: true, body: hashtags }
    ];
  }

  function toneLabel(tone) {
    return {
      warm: "varm och personlig",
      professional: "trygg och professionell",
      playful: "lättsam och lekfull",
      premium: "lugn och exklusiv"
    }[tone] || "personlig";
  }

  function createCard(card, index) {
    const article = document.createElement("article");
    article.className = "result-card" + (card.wide ? " wide" : "");
    article.dataset.outputCard = "true";

    const head = document.createElement("div");
    head.className = "result-card-head";
    const title = document.createElement("h3");
    title.textContent = card.title;
    const tag = document.createElement("span");
    tag.className = "result-tag";
    tag.textContent = card.tag;
    head.append(title, tag);

    const body = document.createElement("p");
    body.textContent = card.body;

    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "copy-button";
    copy.dataset.copy = String(index);
    copy.textContent = "Kopiera text";
    copy.addEventListener("click", async () => {
      const ok = await copyText(card.title + "\n\n" + card.body);
      copy.textContent = ok ? "Kopierad ✓" : "Markera och kopiera";
      copy.dataset.copied = ok ? "true" : "false";
    });

    article.append(head, body, copy);
    return article;
  }

  async function copyText(text) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (error) {
      // Use the selection fallback below.
    }
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (error) { ok = false; }
    area.remove();
    return ok;
  }

  function allText() {
    return currentCards.map((card) => card.title + "\n" + card.body).join("\n\n------------------------------\n\n");
  }

  function render() {
    const data = getFormData();
    currentCards = buildCards(data);
    resultCards.replaceChildren(...currentCards.map(createCard));
    byId("resultSummary").textContent = currentCards.length + " delar skapade för " + data.businessName + ". Mål: " + ({
      visits: "fler besök", bookings: "fler bokningar", sales: "ökad försäljning", leads: "fler förfrågningar"
    }[data.goal] || "mer synlighet") + ".";
    emptyState.hidden = true;
    resultsContent.hidden = false;
    saveDraft();
    resultsContent.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    if (!getFormData().channels.length) {
      formStatus.textContent = "Välj minst en kanal eller markera den du vill testa först.";
      return;
    }
    render();
  });

  form.addEventListener("input", saveDraft);
  form.addEventListener("change", saveDraft);

  byId("sampleBtn").addEventListener("click", () => {
    byId("businessName").value = "Lilla Bageriet";
    byId("businessType").value = "cafe";
    byId("location").value = "Örebro";
    byId("audience").value = "boende i närområdet";
    byId("offer").value = "nybakade kanelbullar och färskt bröd varje morgon";
    byId("tone").value = "warm";
    byId("goal").value = "visits";
    byId("cta").value = "Titta in och säg hej";
    form.querySelectorAll('input[name="channels"]').forEach((item) => {
      item.checked = item.value === "Instagram" || item.value === "Facebook";
    });
    saveDraft();
    formStatus.textContent = "Exemplet är ifyllt. Ändra gärna uppgifterna innan du skapar paketet.";
  });

  byId("copyAllBtn").addEventListener("click", async () => {
    const ok = await copyText(allText());
    byId("copyAllBtn").textContent = ok ? "Kopierat ✓" : "Kopiering misslyckades";
  });

  byId("exportBtn").addEventListener("click", () => {
    if (!currentCards.length) return;
    const blob = new Blob(["KAMPANJPAKET\n\n" + allText()], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const safeName = (value("businessName") || "kampanj").toLowerCase().replace(/[^a-zåäö0-9]+/g, "-").replace(/^-|-$/g, "");
    link.href = url;
    link.download = (safeName || "kampanj") + "-kampanjpaket.txt";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  });

  byId("printBtn").addEventListener("click", () => window.print());

  restoreDraft();
})();
