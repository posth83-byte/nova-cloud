(() => {
  "use strict";

  const WildFrontierGame = {
    canvas: null,
    ctx: null,
    score: 0,
    health: 100,
    items: [],
    keys: Object.create(null),
    isRunning: false,
    animationFrame: null,
    lastSpawn: 0,
    lastFrame: 0,
    player: { x: 0, y: 0, size: 28, speed: 360 },

    init() {
      this.canvas = document.getElementById("wf-canvas");
      if (!this.canvas) {
        console.error("Wild Frontier: canvas #wf-canvas saknas.");
        return;
      }

      this.ctx = this.canvas.getContext("2d");
      if (!this.ctx) {
        console.error("Wild Frontier: kunde inte skapa 2D-context.");
        return;
      }

      this.resizeCanvas();
      this.player.y = this.canvas.height - this.player.size - 18;
      this.player.x = (this.canvas.width - this.player.size) / 2;

      window.addEventListener("resize", () => this.resizeCanvas());
      window.addEventListener("keydown", (event) => {
        this.keys[event.key] = true;
        if (["ArrowLeft", "ArrowRight", " "].includes(event.key)) event.preventDefault();
      });
      window.addEventListener("keyup", (event) => { this.keys[event.key] = false; });
      window.addEventListener("blur", () => { this.keys = Object.create(null); });

      this.canvas.addEventListener("pointermove", (event) => this.movePlayer(event));
      this.canvas.addEventListener("pointerdown", (event) => {
        this.canvas.setPointerCapture?.(event.pointerId);
        this.movePlayer(event);
      });

      const startButton = document.getElementById("wf-start-btn");
      if (startButton) startButton.addEventListener("click", () => this.startGame());

      this.renderMenuState();
    },

    resizeCanvas() {
      if (!this.canvas) return;
      const rect = this.canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(1, Math.round(rect.width * dpr));
      const height = Math.max(1, Math.round(rect.height * dpr));
      if (this.canvas.width !== width || this.canvas.height !== height) {
        this.canvas.width = width;
        this.canvas.height = height;
      }
      this.player.size = Math.max(22, Math.min(34, width * 0.065));
      this.player.y = height - this.player.size - 18 * dpr;
      this.player.x = Math.max(0, Math.min(this.player.x, width - this.player.size));
      this.render();
    },

    movePlayer(event) {
      if (!this.canvas) return;
      const rect = this.canvas.getBoundingClientRect();
      if (!rect.width) return;
      const scaleX = this.canvas.width / rect.width;
      const x = (event.clientX - rect.left) * scaleX - this.player.size / 2;
      this.player.x = Math.max(0, Math.min(this.canvas.width - this.player.size, x));
    },

    startGame() {
      if (!this.canvas || !this.ctx) return;
      if (this.animationFrame) cancelAnimationFrame(this.animationFrame);
      this.score = 0;
      this.health = 100;
      this.items = [];
      this.keys = Object.create(null);
      this.lastSpawn = 0;
      this.lastFrame = 0;
      this.player.x = (this.canvas.width - this.player.size) / 2;
      this.isRunning = true;

      const overlay = document.getElementById("wf-overlay");
      if (overlay) overlay.classList.add("hidden");
      this.setStatus("AKTIV", "text-green-400");
      this.updateHud();
      this.animationFrame = requestAnimationFrame((time) => this.loop(time));
    },

    setStatus(label, className) {
      const status = document.getElementById("wf-status");
      if (status) {
        status.textContent = label;
        status.className = className + " font-semibold";
      }
    },

    updateHud() {
      const score = document.getElementById("wf-score");
      const health = document.getElementById("wf-health");
      if (score) score.textContent = String(this.score);
      if (health) health.textContent = String(this.health);
    },

    update(delta, time) {
      if (!this.isRunning) return;

      const direction =
        (this.keys.ArrowRight || this.keys.d || this.keys.D ? 1 : 0) -
        (this.keys.ArrowLeft || this.keys.a || this.keys.A ? 1 : 0);
      this.player.x += direction * this.player.speed * (this.canvas.width / 600) * delta;
      this.player.x = Math.max(0, Math.min(this.canvas.width - this.player.size, this.player.x));

      if (!this.lastSpawn || time - this.lastSpawn > 650) {
        this.lastSpawn = time;
        const size = Math.max(14, this.canvas.width * 0.035);
        this.items.push({
          x: Math.random() * Math.max(1, this.canvas.width - size),
          y: -size,
          size,
          speed: (150 + Math.random() * 130) * (this.canvas.width / 600),
          type: Math.random() < 0.32 ? "hazard" : "resource"
        });
      }

      for (let i = this.items.length - 1; i >= 0; i--) {
        const item = this.items[i];
        item.y += item.speed * delta;

        const hit =
          this.player.x < item.x + item.size &&
          this.player.x + this.player.size > item.x &&
          this.player.y < item.y + item.size &&
          this.player.y + this.player.size > item.y;

        if (hit) {
          if (item.type === "resource") {
            this.score += 10;
          } else {
            this.health = Math.max(0, this.health - 20);
          }
          this.items.splice(i, 1);
          if (this.health <= 0) {
            this.gameOver();
            return;
          }
        } else if (item.y > this.canvas.height + item.size) {
          this.items.splice(i, 1);
        }
      }
      this.updateHud();
    },

    render() {
      if (!this.ctx || !this.canvas) return;
      const ctx = this.ctx;
      const width = this.canvas.width;
      const height = this.canvas.height;

      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = "#090d16";
      ctx.fillRect(0, 0, width, height);

      ctx.fillStyle = "#334155";
      for (let i = 0; i < 32; i++) {
        const x = (i * 97) % width;
        const y = (i * 173 + (this.lastFrame * 0.035)) % height;
        ctx.fillRect(x, y, 2, 2);
      }

      for (const item of this.items) {
        ctx.beginPath();
        ctx.fillStyle = item.type === "resource" ? "#10b981" : "#ef4444";
        ctx.shadowColor = ctx.fillStyle;
        ctx.shadowBlur = 12;
        ctx.arc(item.x + item.size / 2, item.y + item.size / 2, item.size / 2, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.shadowColor = "#06b6d4";
      ctx.shadowBlur = 16;
      ctx.fillStyle = "#06b6d4";
      ctx.fillRect(this.player.x, this.player.y, this.player.size, this.player.size);
      ctx.shadowBlur = 0;
    },

    renderMenuState() {
      this.items = [];
      this.render();
      if (this.ctx && this.canvas) {
        this.ctx.fillStyle = "#67e8f9";
        this.ctx.font = "600 16px sans-serif";
        this.ctx.textAlign = "center";
        this.ctx.fillText("REDO FÖR EXPEDITION", this.canvas.width / 2, this.canvas.height / 2);
      }
    },

    loop(time) {
      if (!this.isRunning) return;
      const delta = this.lastFrame ? Math.min((time - this.lastFrame) / 1000, 0.05) : 0;
      this.lastFrame = time;
      this.update(delta, time);
      if (!this.isRunning) return;
      this.render();
      this.animationFrame = requestAnimationFrame((nextTime) => this.loop(nextTime));
    },

    gameOver() {
      this.isRunning = false;
      if (this.animationFrame) cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
      this.setStatus("AVSLUTAD", "text-red-400");

      const overlay = document.getElementById("wf-overlay");
      if (overlay) {
        overlay.classList.remove("hidden");
        overlay.replaceChildren();

        const heading = document.createElement("h3");
        heading.className = "font-orbitron text-xl md:text-2xl font-bold text-red-500 mb-2";
        heading.textContent = "EXPEDITION MISSLYCKAD";

        const message = document.createElement("p");
        message.className = "text-slate-300 text-xs md:text-sm mb-4";
        message.textContent = "Du samlade " + this.score + " provisioner innan hälsan tog slut.";

        const button = document.createElement("button");
        button.className = "font-orbitron bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-8 py-3 rounded-xl";
        button.textContent = "FÖRSÖK IGEN";
        button.addEventListener("click", () => this.startGame());

        overlay.append(heading, message, button);
      }
    }
  };

  window.addEventListener("DOMContentLoaded", () => WildFrontierGame.init());
})();
