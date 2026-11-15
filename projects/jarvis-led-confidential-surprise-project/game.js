class QuantumDash {
    constructor() {
        this.canvas = document.getElementById('j-canvas');
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        
        this.score = 0;
        this.hs = 0;
        this.playing = false;
        this.animId = null;
        
        this.player = {
            x: 40,
            y: 200,
            w: 24,
            h: 24,
            vy: 0,
            gravity: 0.55,
            jump: -9.5,
            grounded: false
        };
        
        this.obs = [];
        this.timer = 0;
        this.interval = 85;
        this.speed = 4.5;
        this.groundLevel = 260;
        
        this.init();
    }

    init() {
        this.canvas.width = 640;
        this.canvas.height = 360;
        
        this.hs = parseInt(localStorage.getItem('q_hs') || '0', 10);
        const hsEl = document.getElementById('j-hs');
        if (hsEl) hsEl.innerText = this.hs;

        const btn = document.getElementById('j-btn');
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.start();
            });
        }

        this.canvas.addEventListener('click', () => this.jump());
        window.addEventListener('keydown', (e) => {
            if (e.code === 'Space' || e.code === 'ArrowUp') {
                e.preventDefault();
                this.jump();
            }
        });

        this.renderInitialState();
    }

    start() {
        this.score = 0;
        this.obs = [];
        this.timer = 0;
        this.speed = 4.5;
        this.player.y = this.groundLevel - this.player.h;
        this.player.vy = 0;
        this.player.grounded = true;
        this.playing = true;

        const overlay = document.getElementById('j-overlay');
        if (overlay) overlay.classList.add('hidden');

        const status = document.getElementById('j-status');
        if (status) {
            status.innerText = 'SPELAR';
            status.className = 'text-green-400 font-bold';
        }

        if (this.animId) cancelAnimationFrame(this.animId);
        this.loop();
    }

    jump() {
        if (!this.playing) {
            this.start();
            return;
        }
        if (this.player.grounded) {
            this.player.vy = this.player.jump;
            this.player.grounded = false;
        }
    }

    update() {
        this.score++;
        const scoreEl = document.getElementById('j-score');
        if (scoreEl) scoreEl.innerText = this.score;

        if (this.score % 350 === 0) {
            this.speed += 0.5;
        }

        this.player.vy += this.player.gravity;
        this.player.y += this.player.vy;

        if (this.player.y >= this.groundLevel - this.player.h) {
            this.player.y = this.groundLevel - this.player.h;
            this.player.vy = 0;
            this.player.grounded = true;
        }

        this.timer++;
        if (this.timer >= this.interval) {
            this.timer = 0;
            let h = 25 + Math.random() * 40;
            this.obs.push({
                x: this.canvas.width,
                y: this.groundLevel - h,
                w: 20,
                h: h
            });
        }

        for (let i = this.obs.length - 1; i >= 0; i--) {
            let o = this.obs[i];
            o.x -= this.speed;

            if (
                this.player.x < o.x + o.w &&
                this.player.x + this.player.w > o.x &&
                this.player.y < o.y + o.h &&
                this.player.y + this.player.h > o.y
            ) {
                this.gameOver();
                return;
            }

            if (o.x + o.w < 0) {
                this.obs.splice(i, 1);
            }
        }
    }

    render() {
        this.ctx.fillStyle = '#020617';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        this.ctx.strokeStyle = '#06b6d4';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.moveTo(0, this.groundLevel);
        this.ctx.lineTo(this.canvas.width, this.groundLevel);
        this.ctx.stroke();

        this.ctx.fillStyle = '#06b6d4';
        this.ctx.shadowColor = '#06b6d4';
        this.ctx.shadowBlur = 12;
        this.ctx.fillRect(this.player.x, this.player.y, this.player.w, this.player.h);

        this.ctx.fillStyle = '#38bdf8';
        for (let o of this.obs) {
            this.ctx.shadowColor = '#38bdf8';
            this.ctx.shadowBlur = 8;
            this.ctx.fillRect(o.x, o.y, o.w, o.h);
        }

        this.ctx.shadowBlur = 0;
    }

    renderInitialState() {
        this.render();
    }

    loop() {
        if (!this.playing) return;
        this.update();
        this.render();
        this.animId = requestAnimationFrame(() => this.loop());
    }

    gameOver() {
        this.playing = false;
        cancelAnimationFrame(this.animId);

        if (this.score > this.hs) {
            this.hs = this.score;
            localStorage.setItem('q_hs', this.hs);
            const hsEl = document.getElementById('j-hs');
            if (hsEl) hsEl.innerText = this.hs;
        }

        const status = document.getElementById('j-status');
        if (status) {
            status.innerText = 'KRASCH';
            status.className = 'text-red-500 font-bold';
        }

        const overlay = document.getElementById('j-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
            const h3 = overlay.querySelector('h3');
            if (h3) h3.innerText = `GAME OVER - POÄNG: ${this.score}`;
            const btn = overlay.querySelector('button');
            if (btn) btn.innerText = 'SPELA IGEN';
        }
    }
}

window.addEventListener('DOMContentLoaded', () => {
    window.quantumGame = new QuantumDash();
});