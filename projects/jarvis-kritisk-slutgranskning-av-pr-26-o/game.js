(function () {
  'use strict';
  class GameEngine {
    constructor(canvasId) {
      this.canvas = document.getElementById(canvasId);
      if (!this.canvas) throw new Error('Spelcanvas saknas: ' + canvasId);
      this.ctx = this.canvas.getContext('2d');
      if (!this.ctx) throw new Error('Canvas 2D stöds inte.');
      this.isRunning = false; this.isPaused = false; this.frame = 0;
      this.score = 0; this.lives = 3; this.raf = 0;
      this.player = { x: 55, y: 180, width: 28, height: 28, speed: 5, color: '#00ffcc' };
      this.keys = Object.create(null);
      this.obstacles = []; this.particles = []; this.spawnTimer = 0; this.spawnInterval = 75;
      this.bindInput(); this.resize();
      window.addEventListener('resize', () => this.resize());
      this.render();
    }
    resize() {
      const box = this.canvas.parentElement;
      if (!box) return;
      const width = Math.max(280, box.clientWidth);
      const height = Math.max(220, box.clientHeight);
      if (this.canvas.width !== width || this.canvas.height !== height) {
        this.canvas.width = width; this.canvas.height = height;
      }
      this.player.x = Math.min(this.player.x, width - this.player.width);
      this.player.y = Math.min(this.player.y, height - this.player.height);
      if (!this.isRunning) this.render();
    }
    bindInput() {
      const keyMap = { ArrowUp:'up', ArrowDown:'down', ArrowLeft:'left', ArrowRight:'right', ' ':'up', w:'up', s:'down', a:'left', d:'right' };
      window.addEventListener('keydown', e => {
        const key = keyMap[e.key];
        if (key) { this.keys[key] = true; e.preventDefault(); }
      });
      window.addEventListener('keyup', e => { const key = keyMap[e.key]; if (key) this.keys[key] = false; });
      const bind = (id, direction) => {
        const button = document.getElementById(id);
        if (!button) return;
        const down = e => { e.preventDefault(); this.keys[direction] = true; };
        const up = e => { e.preventDefault(); this.keys[direction] = false; };
        button.addEventListener('pointerdown', down);
        ['pointerup','pointerleave','pointercancel'].forEach(type => button.addEventListener(type, up));
        button.addEventListener('contextmenu', e => e.preventDefault());
      };
      bind('btnUp','up'); bind('btnDown','down'); bind('btnLeft','left'); bind('btnRight','right'); bind('btnAction','up');
    }
    start() {
      if (this.isRunning) return;
      this.isRunning = true; this.isPaused = false; this.score = 0; this.lives = 3;
      this.obstacles = []; this.particles = []; this.spawnTimer = 0; this.spawnInterval = 75;
      this.player.x = 55; this.player.y = Math.max(0, this.canvas.height / 2);
      const overlay = document.getElementById('gameOverlay');
      if (overlay) overlay.style.display = 'none';
      cancelAnimationFrame(this.raf); this.loop();
    }
    stop() {
      this.isRunning = false; this.isPaused = false; cancelAnimationFrame(this.raf);
      const overlay = document.getElementById('gameOverlay');
      if (overlay) {
        overlay.style.display = 'flex';
        const title = overlay.querySelector('h3');
        if (title) title.textContent = 'SPEL AVSLUTAT – POÄNG: ' + this.score;
        const button = document.getElementById('startGameBtn');
        if (button) button.textContent = 'Spela igen';
      }
      this.render();
    }
    pause() {
      if (!this.isRunning) return;
      this.isPaused = !this.isPaused;
      if (this.isPaused) cancelAnimationFrame(this.raf);
      else this.loop();
    }
    update() {
      const p = this.player;
      if (this.keys.up) p.y -= p.speed;
      if (this.keys.down) p.y += p.speed;
      if (this.keys.left) p.x -= p.speed;
      if (this.keys.right) p.x += p.speed;
      p.x = Math.max(0, Math.min(this.canvas.width - p.width, p.x));
      p.y = Math.max(0, Math.min(this.canvas.height - p.height, p.y));
      if (++this.spawnTimer >= this.spawnInterval) {
        this.spawnTimer = 0;
        const size = 18 + Math.random() * 24;
        this.obstacles.push({ x:this.canvas.width, y:Math.random()*(this.canvas.height-size), width:size, height:size, speed:3+Math.random()*2 });
        this.spawnInterval = Math.max(35, this.spawnInterval - 0.15);
      }
      for (let i=this.obstacles.length-1;i>=0;i--) {
        const o=this.obstacles[i]; o.x -= o.speed;
        if (p.x < o.x+o.width && p.x+p.width > o.x && p.y < o.y+o.height && p.y+p.height > o.y) {
          this.obstacles.splice(i,1); this.lives--;
          if (this.lives <= 0) { this.stop(); return; }
        } else if (o.x+o.width < 0) { this.obstacles.splice(i,1); this.score += 10; }
      }
    }
    render() {
      const c=this.ctx, w=this.canvas.width, h=this.canvas.height;
      c.clearRect(0,0,w,h); c.fillStyle='#050505'; c.fillRect(0,0,w,h);
      c.fillStyle=this.player.color; c.shadowBlur=14; c.shadowColor=this.player.color;
      c.fillRect(this.player.x,this.player.y,this.player.width,this.player.height); c.shadowBlur=0;
      c.fillStyle='#ef4444'; this.obstacles.forEach(o=>c.fillRect(o.x,o.y,o.width,o.height));
      c.fillStyle='#f3f4f6'; c.font='14px system-ui'; c.fillText('Poäng: '+this.score,14,22); c.fillText('Liv: '+this.lives,14,42);
      if (this.isPaused) { c.fillStyle='rgba(0,0,0,.55)'; c.fillRect(0,0,w,h); c.fillStyle='#fff'; c.fillText('PAUS',w/2-18,h/2); }
    }
    loop() {
      if (!this.isRunning || this.isPaused) return;
      this.update(); this.render();
      if (this.isRunning && !this.isPaused) this.raf = requestAnimationFrame(() => this.loop());
    }
  }
  window.JarvisGame = GameEngine;
})();
