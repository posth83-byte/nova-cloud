class JarvisCatcher {
    constructor() {
        this.canvas = document.getElementById('gameCanvas');
        if (!this.canvas) return;
        
        this.ctx = this.canvas.getContext('2d');
        this.score = 0;
        this.lives = 3;
        this.isGameRunning = false;
        this.animationId = null;
        
        this.player = {
            x: this.canvas.width / 2 - 40,
            y: this.canvas.height - 50,
            width: 80,
            height: 20,
            speed: 8,
            dx: 0
        };
        
        this.items = [];
        this.itemSpawnTimer = 0;
        this.itemSpawnInterval = 60; // frames
        
        this.keys = {
            left: false,
            right: false
        };

        this.initElements();
        this.initListeners();
    }

    initElements() {
        this.startBtn = document.getElementById('startGameBtn');
        this.scoreEl = document.getElementById('gameScore');
        this.livesEl = document.getElementById('gameLives');
        this.overlayEl = document.getElementById('gameOverlay');
        this.overlayText = document.getElementById('gameOverlayText');

        if (this.startBtn) {
            this.startBtn.addEventListener('click', () => this.startGame());
        }
    }

    initListeners() {
        window.addEventListener('keydown', (e) => {
            if (!this.isGameRunning) return;
            if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {
                this.keys.left = true;
            } else if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') {
                this.keys.right = true;
            }
        });

        window.addEventListener('keyup', (e) => {
            if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {
                this.keys.left = false;
            } else if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') {
                this.keys.right = false;
            }
        });

        // Touch support for mobile devices
        let touchStartX = 0;
        this.canvas.addEventListener('touchstart', (e) => {
            if (!this.isGameRunning) return;
            touchStartX = e.touches[0].clientX;
            e.preventDefault();
        }, { passive: false });

        this.canvas.addEventListener('touchmove', (e) => {
            if (!this.isGameRunning) return;
            const touchX = e.touches[0].clientX;
            const diff = touchX - touchStartX;
            this.player.x += diff * 0.8;
            touchStartX = touchX;

            // Constrain to canvas
            if (this .player.x < 0) this.player.x = 0;
            if (this.player.x + this.player.width > this.canvas.width) {
                this.player.x = this.canvas.width - this.player.width;
            }
            e.preventDefault();
        }, { passive: false });
    }

    startGame() {
        try {
            this.score = 0;
            this.lives = 3;
            this.items = [];
            this.itemSpawnTimer = 0;
            this.isGameRunning = true;
            this.player.x = this.canvas.width / 2 - 40;

            if (this.overlayEl) {
                this.overlayEl.classList.add('hidden');
            }
            if (this.startBtn) {
                this.startBtn.textContent = 'Återstarta Spel';
            }

            this.updateUI();
            
            if (this.animationId) {
                cancelAnimationFrame(this.animationId);
            }
            
            this.loop();
        } catch (error) {
            console.error('Fel vid start av spel:', error);
        }
    }

    stopGame(message) {
        this.isGameRunning = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        if (this.overlayEl && this.overlayText) {
            this.overlayText.textContent = message;
            this.overlayEl.classList.remove('hidden');
        }
        if (this.startBtn) {
            this.startBtn.textContent = 'Spela Igen';
        }
    }

    update() {
        // Player movement via keyboard
        if (this.keys.left) {
            this.player.x -= this.player.speed;
        }
        if (this.keys.right) {
            this.player.x += this.player.speed;
        }

        // Constrain player position
        if (this.player.x < 0) this.player.x = 0;
        if (this.player.x + this.player.width > this.canvas.width) {
            this.player.x = this.canvas.width - this.player.width;
        }

        // Item spawning
        this.itemSpawnTimer++;
        if (this.itemSpawnTimer >= this.itemSpawnInterval) {
            this.itemSpawnTimer = 0;
            this.spawnItem();
        }

        // Update items
        for (let i = this.items.length - 1; i >= 0; i--) {
            let item = this.items[i];
            item.y += item.speed;

            // Collision with player
            if (
                item.x < this.player.x + this.player.width &&
                item.x + item.size > this.player.x &&
                item.y < this.player.y + this.player.height &&
                item.y + item.size > this.player.y
            ) {
                if (item.type === 'good') {
                    this.score += 10;
                } else {
                    this.lives -= 1;
                }
                this.items.splice(i, 1);
                this.updateUI();

                if (this.lives <= 0) {
                    this.stopGame('SYSTEMET KRASHADE - SLUT PÅ LIV');
                    return;
                }
                continue;
            }

            // Remove out of bounds
            if (item.y > this.canvas.height) {
                if (item.type === 'good') {
                    this.lives -= 1;
                    this.updateUI();
                    if (this.lives <= 0) {
                        this.stopGame('SYSTEMET KRASHADE - SLUT PÅ LIV');
                        return;
                    }
                }
                this.items.splice(i, 1);
            }
        }
    }

    spawnItem() {
        const isGood = Math.random() > 0.3;
        const size = 24;
        const x = Math.random() * (this.canvas.width - size);
        const speed = 2 + Math.random() * 3 + (this.score / 100);
        
        this.items.push({
            x: x,
            y: -size,
            size: size,
            speed: speed > 7 ? 7 : speed,
            type: isGood ? 'good' : 'bad',
            symbol: isGood ? '⚡' : '🔥'
        });
    }

    draw() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw grid background effect
        this.ctx.strokeStyle = 'rgba(0, 240, 255, 0.05)';
        this.ctx.lineWidth = 1;
        for (let x = 0; x < this.canvas.width; x += 20) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
            this.ctx.stroke();
        }

        // Draw player (JARVIS Core Catcher)
        this.ctx.shadowBlur = 15;
        this.ctx.shadowColor = '#00f0ff';
        this.ctx.fillStyle = '#00f0ff';
        this.ctx.fillRect(this.player.x, this.player.y, this.player.width, this.player.height);
        
        // Inner core line
        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillRect(this.player.x + 10, this.player.y + 6, this.player.width - 20, 4);

        // Draw items
        this.ctx.shadowBlur = 10;
        for (let item of this.items) {
            this.ctx.shadowColor = item.type === 'good' ? '#00ff66' : '#ff0055';
            this.ctx.fillStyle = item.type === 'good' ? '#00ff66' : '#ff0055';
            
            this.ctx.beginPath();
            this.ctx.arc(item.x + item.size / 2, item.y + item.size / 2, item.size / 2, 0, Math.PI * 2);
            this.ctx.fill();

            this.ctx.font = '14px sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText(item.symbol, item.x + item.size / 2, item.y + item.size / 2);
        }

        this.ctx.shadowBlur = 0;
    }

    loop() {
        if (!this.isGameRunning) return;
        this.update();
        this.draw();
        this.animationId = requestAnimationFrame(() => this.loop());
    }

    updateUI() {
        if (this.scoreEl) this.scoreEl.textContent = this.score;
        if (this.livesEl) this.livesEl.textContent = this.lives;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.jarvisGame = new JarvisCatcher();
});