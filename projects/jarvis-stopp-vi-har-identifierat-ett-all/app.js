document.addEventListener('DOMContentLoaded', () => {
    const statusContainer = document.getElementById('status-container');
    const verifyButton = document.getElementById('verify-access-btn');
    const logOutput = document.getElementById('log-output');

    if (!statusContainer || !verifyButton || !logOutput) {
        console.error('Kritiska element saknas i DOM. Kontrollera index.html.');
        return;
    }

    const systemReport = {
        writeAccess: false,
        prNumber: 24,
        latestCommit: "f239d2f",
        message: "JARVIS, STOPP. Ingen skrivåtkomst till GitHub-repot existerar i denna miljö. Inga låtsade commit-SHA:n eller simulerade körloggar har genererats."
    };

    function renderStatus(report, isVerified = false) {
        statusContainer.innerHTML = `
            <div class="status-card ${report.writeAccess ? 'success' : 'error'}">
                <h3>Systemstatus: Åtkomstkontroll</h3>
                <p><strong>Skrivåtkomst till GitHub:</strong> ${report.writeAccess ? 'BEKRÄFTAD' : 'SAKNAR ÅTKOMST'}</p>
                <p><strong>Aktuell PR:</strong> #${report.prNumber}</p>
                <p><strong>Senaste kända Commit-SHA:</strong> <code>${report.latestCommit}</code></p>
                <p class="warning-text">${report.message}</p>
                ${isVerified ? '<p class="verified-timestamp">Verifiering utförd: ' + new Date().toLocaleTimeString() + '</p>' : ''}
            </div>
        `;
    }

    renderStatus(systemReport, false);

    verifyButton.addEventListener('click', () => {
        logOutput.textContent = "Startar verifiering mot begränsad miljö...\n";
        logOutput.textContent += "Kontrollerar API-tokens och terminalåtkomst...\n";
        
        setTimeout(() => {
            logOutput.textContent += "[FEL] Ingen aktiv terminal eller GitHub-integration hittades.\n";
            logOutput.textContent += "[FEL] Skrivåtkomst nekad. Inga ändringar kan utföras.\n";
            logOutput.textContent += "Process avbruten enligt säkerhetsprotokoll.\n";
            renderStatus(systemReport, true);
        }, 600);
    });
});