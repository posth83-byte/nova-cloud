// Rita HUD (Poäng och missade)
        ctx.fillStyle = '#f8fafc';
        ctx.font = '14px system-ui, sans-serif';
        ctx.fillText(`Poäng: ${score}`, 15, 25);
        ctx.fillText(`Missade: ${missed}/5`, canvas.width - 100, 25);
    }

    function loop() {
        if (!isRunning) return;
        update();
        if (isRunning) {
            render();
            animationFrameId = requestAnimationFrame(loop);
        }
    }

    function gameOver() {
        stop();
        ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = '#ef4444';
        ctx.font = 'bold 22px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('SPELET ÄR SLUT', canvas.width / 2, canvas.height / 2 - 15);

        ctx.fillStyle = '#f8fafc';
        ctx.font = '16px system-ui, sans-serif';
        ctx.fillText(`Slutresultat: ${score} poäng`, canvas.width / 2, canvas.height / 2 + 15);
        ctx.textAlign = 'left'; // Återställ
    }

    function drawStartScreen() {
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = '#38bdf8';
        ctx.font = 'bold 20px system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('JARVIS CATCHER', canvas.width / 2, canvas.height / 2 - 20);

        ctx.fillStyle = '#94a3b8';
        ctx.font = '14px system-ui, sans-serif';
        ctx.fillText('Använd PILAR eller A/D för att flytta', canvas.width / 2, canvas.height / 2 + 10);
        ctx.fillText('Klicka på Start för att börja', canvas.width / 2, canvas.height / 2 + 35);
        ctx.textAlign = 'left';
    }

    // Officiellt publika gränssnittet (Revealing Module Pattern)
    return {
        init: init,
        start: start,
        stop: stop,
        destroy: destroy,
        getScore: function() { return score; },
        isGameRunning: function() { return isRunning; }
    };

})();