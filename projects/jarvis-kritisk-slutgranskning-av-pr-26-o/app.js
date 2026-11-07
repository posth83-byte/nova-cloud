// JARVIS systemportal – riktig diagnostik och fungerande gränssnitt.
document.addEventListener('DOMContentLoaded', () => {
  const $ = (id) => document.getElementById(id);
  const menuToggle = $('menuToggle');
  const mainNav = $('mainNav');
  const panels = [...document.querySelectorAll('main .panel')];
  const navButtons = [...document.querySelectorAll('.nav-btn')];

  function showPanel(id) {
    panels.forEach(panel => {
      const active = panel.id === id;
      panel.classList.toggle('active', active);
      panel.style.display = active ? 'block' : 'none';
    });
    window.dispatchEvent(new Event('resize'));
    navButtons.forEach(button => {
      const active = button.dataset.target === id;
      button.classList.toggle('active', active);
      button.setAttribute('aria-current', active ? 'page' : 'false');
    });
  }
  navButtons.forEach(button => button.addEventListener('click', () => {
    showPanel(button.dataset.target);
    mainNav?.classList.remove('open');
  }));
  menuToggle?.addEventListener('click', () => {
    const open = mainNav.classList.toggle('open');
    menuToggle.setAttribute('aria-expanded', String(open));
  });
  showPanel('panel-tasks');

  const taskInput = $('taskInput');
  const taskList = $('taskList');
  function addTask() {
    const value = taskInput?.value.trim();
    if (!value || !taskList) return;
    const item = document.createElement('li');
    item.className = 'task-item';
    item.style.cssText = 'background:#1f2937;padding:.75rem;border-radius:4px;display:flex;justify-content:space-between;align-items:center;gap:1rem';
    const label = document.createElement('span');
    label.textContent = value;
    const done = document.createElement('button');
    done.className = 'btn';
    done.type = 'button';
    done.textContent = 'Klar';
    done.addEventListener('click', () => item.remove());
    item.append(label, done);
    taskList.append(item);
    taskInput.value = '';
    taskInput.focus();
  }
  $('addTaskBtn')?.addEventListener('click', addTask);
  taskInput?.addEventListener('keydown', event => {
    if (event.key === 'Enter') addTask();
  });
  taskList?.querySelectorAll('li button').forEach(button => {
    button.addEventListener('click', () => button.closest('li')?.remove());
  });

  function setStatus(kind, state, message) {
    const text = $(`status-${kind}`);
    const card = $(`card-${kind}`);
    if (!text || !card) return;
    text.textContent = message;
    card.classList.toggle('ok', state === 'ok');
    card.classList.toggle('error', state === 'error');
  }
  async function fetchJson(url, options = {}) {
    const response = await fetch(url, { cache: 'no-store', ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }
  $('runDiagBtn')?.addEventListener('click', async () => {
    const button = $('runDiagBtn');
    button.disabled = true;
    button.textContent = 'Testar...';
    setStatus('gemini', 'pending', 'Kontrollerar NOVA Cloud och gör ett riktigt AI-anrop…');
    setStatus('supabase', 'pending', 'Kontrollerar serverns minneslagring…');
    try {
      const health = await fetchJson('/health');
      if (health.status !== 'online') throw new Error('Backend rapporterar inte online');
      const status = await fetchJson('/api/status');
      if (!status.gemini_configured) {
        setStatus('gemini', 'error', 'Backend nås, men GEMINI_API_KEY saknas. Ingen AI-test kördes.');
      } else {
        const answer = await fetchJson('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: 'Svara med exakt ordet OK. Detta är ett kort diagnostiskt test.' })
        });
        const engine = String(answer.engine || '').toLowerCase();
        if (answer.status === 'online' && answer.reply && engine.includes('gemini')) {
          setStatus('gemini', 'ok', `Riktigt Gemini-anrop lyckades via ${answer.engine}.`);
        } else {
          setStatus('gemini', 'error', `Backend svarade, men Gemini kunde inte bekräftas. Motor: ${answer.engine || 'okänd'}.`);
        }
      }
    } catch (error) {
      setStatus('gemini', 'error', `AI/backend-test misslyckades: ${error.message}`);
    }
    try {
      const memory = await fetchJson('/api/memory/status');
      const storage = String(memory.storage || '').toLowerCase();
      if (storage === 'supabase' && memory.status === 'online' && !memory.error) {
        setStatus('supabase', 'ok', 'Supabase används av minneskärnan och statuskontrollen lyckades.');
      } else if (storage === 'sqlite' && memory.status === 'online') {
        setStatus('supabase', 'error', 'Servern använder SQLite-reservlagring. Supabase är inte aktivt verifierad.');
      } else {
        setStatus('supabase', 'error', memory.error || 'Supabase kunde inte verifieras som aktiv minneslagring.');
      }
    } catch (error) {
      setStatus('supabase', 'error', `Minnes-/databaskontroll misslyckades: ${error.message}`);
    }
    button.disabled = false;
    button.textContent = 'Kör Diagnostik';
  });

  const Game = window.JarvisGame;
  let game = null;
  if (typeof Game === 'function') {
    game = new Game('gameCanvas');
    window.__jarvisGame = game;
    $('startGameBtn')?.addEventListener('click', () => game.start());
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && game?.isRunning) game.pause();
    });
  } else {
    setStatus('gemini', 'error', 'Spelmotorn kunde inte laddas.');
  }
});
