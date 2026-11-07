canvas.getBoundingClientRect();
            const touch = e.touches[0];
            const relativeX = touch.clientX - rect.left;
            // Skala om till canvas interna storlek
            const scaleX = this.canvas.width / rect.width;
            this.player.x = (relativeX * scaleX) - (this.player.size / 2);
            // Begränsa till canvas
            if (this.player.x < 0) this.player.x = 0;
            if (this.player.x > this.canvas.width - this.player.size) {
                this.player.x = this.canvas.width - this.player.size;
            }
            e.preventDefault();
        }, { passive: false });

        this.renderMenuState();
    },

    startGame() {
        this.score = 0;
        this.health = 100;
        this.items = [];
        this.player.x = this.canvas.width / 2 - this.player.size / 2;
        this.isRunning = true;

        const overlay = document.getElementById('wf-overlay');
        if (overlay) overlay.classList.add('hidden');

        const statusEl = document.getElementById('wf-status');
        if (statusEl) {
            statusEl.textContent = 'AKTIV';
            statusEl.className = 'text-green-400 font-semibold';
        }

        this.loop();
    },

    renderMenuState() {
        if (!this.ctx || !this.canvas) return;
        this.ctx.fillStyle = '#090d16';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.fillStyle = '#06b6d4';
        this.ctx.font = 'bold 16px Orbitron';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('REDY FOR EXPEDITION', this.canvas.width / 2, this.canvas.height / 2 - 20);
    },

    update() {
        if (!this.isRunning) return;

        // Tangentbordsstyrning
        if (this.keys['ArrowLeft'] || this.keys['a'] || this.keys['A']) {
            this.player.x -= this.player.speed;
        }
        if (this.keys['ArrowRight'] || this.keys['d'] || this.keys['D']) {
            this.player.x += this.player.speed;
        }

        // Kantkontroll
        if (this.player.x < 0) this.player.x = 0;
        if (this.player.x > this.canvas.width - this.player.size) {
            this.player.x = this.canvas.width - this.player.size;
        }

        // Skapa slumpmässiga resurser / faror
        if (Math.random() < 0.03) {
            const isHazard = Math.random() < 0.35;
            this.items.push({
                x: Math.random() * (this.canvas.width - 20),
                y: -20,
                size: 16,
                speed: 2 + Math.random() * 2,
                type: isHazard ? 'hazard' : 'resource'
            });
        }

        // Uppdatera objekt
        for (let i = this.items.length - 1; i >= 0; i--) {
            let item = this.items[i];
            item.y += item.speed;

            // Kollisionskontroll med spelaren
            if (
                this.player.x < item.x + item.size &&
                this.player.x + this.player.size > item.x &&
                this.player.y < item.y + item.size &&
                this.player.y + this.player.size > item.y
            ) {
                if (item.type === 'resource') {
                    this.score += 10;
                } else {
                    this.health -= 15;
                    if (this.health <= 0) {
                        this.health = 0;
                        this.gameOver();
                    }
                }
                this.items.splice(i, 1);
                continue;
            }

            // Ta bort objekt som nått botten
            if (item.y > this.canvas.height) {
                this.items.splice(i, 1);
            }
        }

        // Uppdatera DOM HUD
        const scoreEl = document.getElementById('wf-score');
        const healthEl = document.getElementById('wf-health');
        if (scoreEl) scoreEl.textContent = this.score;
        if (healthEl) healthEl.textContent = this.health;
    },

    render() {
        if (!this.ctx || !this.canvas) return;

        // Rensa bakgrund
        this.ctx.fillStyle = '#090d16';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Rita stjärnor / markeffekt
        this.ctx.fillStyle = '#1e293b';
        for (let i = 0; i < 5; i++) {
            this.ctx.fillRect((i * 80) + 20, (Date.now() / 50 + i * 40) % this.canvas.height, 2, 2);
        }

        // Rita spelare
        this.ctx.fillStyle = '#06b6d4';
        this.ctx.shadowColor = '#06b6d4';
        this.ctx.shadowBlur = 10;
        this.ctx.fillRect(this.player.x, this.player.y, this.player.size, this.player.size);
        this.ctx.shadowBlur = 0; // Återställ skugga

        // Rita objekt
        for (let item of this.items) {
            this.ctx.fillStyle = item.type === 'resource' ? '#10b981' : '#ef4444';
            this.ctx.beginPath();
            this.ctx.arc(item.x + item.size / 2, item.y + item.size / 2, item.size / 2, 0, Math.PI * 2);
            this.ctx.fill();
        }
    },

    loop() {
        if (!this.isRunning) return;
        this.update();
        this.render();
        requestAnimationFrame(() => this.loop());
    },

    gameOver() {
        this.isRunning = false;
        const overlay = document.getElementById('wf-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
            overlay.innerHTML = `
                <h3 class="font-orbitron text-xl md:text-2xl font-bold text-red-500 mb-2">EXPEDITION MISSLYCKAD</h3>
                <p class="text-slate-300 text-xs md:text-sm mb-4">Du samlade ihop ${this.score} provisioner innan vildmarken tog över.</p>
                <button id="wf-restart-btn" class="font-orbitron bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-8 py-3 rounded-xl transition-all shadow-lg shadow-cyan-500/30 active:scale-95 cursor-pointer">
                    FÖRSÖK IGEN
                </button>
            `;
            const restartBtn = document.getElementById('wf-restart-btn');
            if (restartBtn) {
                restartBtn.addEventListener('click', () => this.startGame());
            }
        }

        const statusEl = document.getElementById('wf-status');
        if (statusEl) {
            statusEl.textContent = 'AVSLUTAD';
            statusEl.className = 'text-red-400 font-semibold';
        }
    }
};

window.addEventListener('DOMContentLoaded', () => {
    WildFrontierGame.init();
});