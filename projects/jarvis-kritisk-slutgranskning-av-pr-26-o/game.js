(function() {
    'use strict';

    class GameEngine {
        constructor(canvasId) {
            this.canvas = document.getElementById(canvasId);
            if (!this.canvas) {
                console.error('Kunde inte hitta canvas-element med ID:', canvasId);
                return;
            }
            this.ctx = this.canvas.getContext('2d');
            this.isRunning = false;
            this.isPaused = false;
            this.score = 0;
            this.lives = 3;

            this.player = {
                x: 50,
                y: 180,
                width: 30,
                height: 30,
                speed: 5,
                color: '#00ffcc'
            };

            this.keys = {
                ArrowUp: false,
                ArrowDown: false,
                ArrowLeft: false,
                ArrowRight: false,
                w: false,
                s: false,
                a: false,
                d: false
            };

            this.obstacles = [];
            this.particles = [];
            this.spawnTimer = 0;
            this.spawnInterval = 90;

            this.setupListeners();
            this.resizeCanvas();
            window.addEventListener('resize', () => this.resizeCanvas());
        }

        resizeCanvas() {
            const parent = this.canvas.parentElement;
            if (parent) {
                this.canvas.width = parent.clientWidth;
                this.canvas.height = parent.clientHeight;
                this.player.y = Math.min(this.player.y, this.canvas.height - this.player.height - 10);
            }
        }

        setupListeners() {
            window.addEventListener('keydown', (e) => {
                if (this.keys.hasOwnProperty(e.key) || e.key.startsWith('Arrow')) {
                    this.keys[e.key] = true;
                    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', ' '].includes(e.key)) {
                        e.preventDefault();
                    }
                }
            });

            window.addEventListener('keyup', (e) => {
                if (this.keys.hasOwnProperty(e.key) || e.key.startsWith('Arrow')) {
                    this.keys[e.key] = false;
                }
            });

            const setupTouchButton = (id, keyName) => {
                const btn = document.getElementById(id);
                if (!btn) return;

                const press = (e) => {
                    e.preventDefault();
                    this.keys[keyName] = true;
                };

                const release = (e) => {
                    e.preventDefault();
                    this.keys[keyName] = false;
                };

                btn.addEventListener('mousedown', press);
                btn.addEventListener('mouseup', release);
                btn.addEventListener('mouseleave', release);
                btn.addEventListener('touchstart', press, { passive: false });
                btn.addEventListener('touchend', release, { passive: false });
                btn.addEventListener('touchcancel', release, { passive: false });
            };

            setupTouchButton('btnUp', 'ArrowUp');
            setupTouchButton('btnDown', 'ArrowDown');
            setupTouchButton('btnLeft', 'ArrowLeft');
            setupTouchButton('btnRight', 'ArrowRight');
        }

        start() {
            if (this.isRunning) return;
            this.isRunning = true;
            this.isPaused = false;
            this.score = 0;
            this.lives = 3;
            this.obstacles = [];
            this.particles = [];
            this.spawnTimer = 0;

            const overlay = document.getElementById('gameOverlay');
            if (overlay) {
                overlay.style.display = 'none';
            }

            this.loop();
        }

        stop() {
            this.isRunning = false;
            const overlay = document.getElementById('gameOverlay');
            if (overlay) {
                overlay.style.display = 'flex';
                const title = overlay.querySelector('h3');
                if (title) title.textContent = 'SPEL AVSLUTAT - POÄNG: ' + this.score;
                const startBtn = document.getElementById('startGameBtn');
                if (startBtn) startBtn.textContent = 'Spela igen';
            }
        }

        pause() {
            this.isPaused = !this.isPaused;
            if (!this.isPaused) {
                this.loop();
            }
        }

        update() {
            if (!this.isRunning || this.isPaused) return;

            if (this.keys.ArrowUp || this.keys.w) {
                this.player.y -= this.player.speed;
            }
            if (this.keys.ArrowDown || this.keys.s) {
                this.player.y += this.player.speed;
            }
            if (this.keys.ArrowLeft || this.keys.a) {
                this.player.x -= this.player.speed;
            }
            if (this.keys.ArrowRight || this.keys.d) {
                this.player.x += this.player.speed;
            }

            if (this.player.x < 0) this.player.x = 0;
            if (this.player.x + this.player.width > this.canvas.width) {
                this.player.x = this.canvas.width - this.player.width;
            }
            if (this.player.y < 0) this.player.y = 0;
            if (this.player.y + this.player.height > this.canvas.height) {
                this.player.y = this.canvas.height - this.player.height;
            }

            this.spawnTimer++;
            if (this.spawnTimer >= this.spawnInterval) {
                this.spawnTimer = 0;
                const size = 20 + Math.random() * 30;
                this.obstacles.push({
                    x: this.canvas.width,
                    y: Math.random() * (this.canvas.height - size),
                    width: size,
                    height: size,
                    speed: 3 + Math.random() * 4,
                    color: '#ef4444'
                });
                if (this.spawnInterval > 40) this.spawnInterval -= 1;
            }

            for (let i = this.obstacles.length - 1; i >= 0; i--) {
                let obs = this.obstacles[i];
                obs.x -= obs.speed;

                if (
                    this.player.x < obs.x + obs.width &&
                    this.player.x + this.player.width > obs.x &&
                    this.player.y < obs.y + obs.height &&
                    this.player.y + this.player.height > obs.y
                ) {
                    this.obstacles.splice(i, 1);
                    this.lives--;
                    this.createParticles(this.player.x, this.player.y, '#ef4444');
                    if (this.lives <= 0) {
                        this.stop();
                        return;
                    }
                } else if (obs.x + obs.width < 0) {
                    this.obstacles.splice(i, 1);
                    this.score += 10;
                }
            }

            for (let i = this.particles.length - 1; i >= 0; i--) {
                let p = this.particles[i];
                p.x += p.vx;
                p.y += p.vy;
                p.life -= 0.03;
                if (p.life <= 0) {
                    this.particles.splice(i, 1);
                }
            }
        }

        createParticles(x, y, color) {
            for (let i = 0; i < 15; i++) {
                this.particles.push({
                    x: x,
                    y: y,
                    vx: (Math.random() - 0.5) * 6,
                    vy: (Math.random() - 0.5) * 6,
                    life: 1.0,
                    color: color
                });
            }
        }

        render() {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

            this.ctx.fillStyle = this.player.color;
            this.ctx.fillRect(this.player.x, this.player.y, this.player.width, this.player.height);

            this.ctx.shadowBlur = 10;
            this.ctx.shadowColor = this.player.color;
            this.ctx.fillRect(this.player.x, this.player.y, this.player.width, this.player.height);
            this.ctx.shadowBlur = 0;

            for (let obs of this.obstacles) {
                this.ctx.fillStyle = obs.color;
                this.ctx.fillRect(obs.x, obs.y, obs.width, obs.height);
            }

            for (let p of this.particles) {
                this.ctx.fillStyle = p.color;
                this.ctx.globalAlpha = p.life;
                this.ctx.fillRect(p.x, p.y, 4, 4);
                this.ctx.globalAlpha = 1.0;
            }

            this.ctx.fillStyle = '#f3f4f6';
            this.ctx.font = '14px sans-serif';
            this.ctx.fillText(`Poäng: ${this.score}`, 15, 25);
            this.ctx.fillText(`Liv: ${this.lives}`, 15, 45);
        }

        loop() {
            if (!this.isRunning || this.isPaused) return;
            this.update();
            this.render();
            requestAnimationFrame(() => this.loop());
        }
    }

    window.JarvisGame = GameEngine;
})();