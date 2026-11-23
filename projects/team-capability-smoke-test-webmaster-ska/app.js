document.addEventListener('DOMContentLoaded', () => {
    const checkStatusBtn = document.getElementById('check-status');
    const statusContainer = document.getElementById('status');
    const logContainer = document.createElement('div');
    
    logContainer.className = 'mt-4 p-3 bg-gray-50 border border-gray-200 rounded text-sm text-gray-700';
    logContainer.innerHTML = '<strong>Händelselogg:</strong> <span id="log-text">Inga händelser ännu.</span>';
    statusContainer.parentNode.appendChild(logContainer);

    const logText = document.getElementById('log-text');

    const statuses = [
        { text: 'Alla system fungerar normalt och branchen är isolerad.', class: 'bg-green-100 text-green-800 border-green-300' },
        { text: 'Varning: QA-granskning pågår för utkast-PR.', class: 'bg-yellow-100 text-yellow-800 border-yellow-300' },
        { text: 'Kritiskt: Saknar betalda tjänster, allt körs lokalt.', class: 'bg-blue-100 text-blue-800 border-blue-300' }
    ];

    let currentIndex = 0;

    checkStatusBtn.addEventListener('click', () => {
        currentIndex = (currentIndex + 1) % statuses.size;
        const current = statuses[currentIndex];

        statusContainer.className = `p-4 shadow-md rounded border ${current.class}`;
        statusContainer.innerHTML = `<p class="font-medium">${current.text}</p>`;

        const timestamp = new Date().toLocaleTimeString();
        logText.textContent = `Status uppdaterad kl ${timestamp} (Testcykel aktiv).`;
        
        console.log(`[TEAM CAPABILITY SMOKE TEST] Status ändrad till: ${current.text} vid ${timestamp}`);
    });

    const linkCSS = document.createElement('link');
    linkCSS.rel = 'stylesheet';
    linkCSS.href = 'style.css';
    document.head.appendChild(linkCSS);

    console.log('app.js har laddats framgångsrikt och händelsehanterare är aktiva.');
});