document.addEventListener('DOMContentLoaded', () => {
    const focusableElementsSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

    const setupAccessibility = () => {
        const interactiveElements = document.querySelectorAll(focusableElementsSelector);
        
        interactiveElements.forEach(el => {
            if (!el.hasAttribute('tabindex')) {
                el.setAttribute('tabindex', '0');
            }
            
            if (el.tagName === 'BUTTON' && !el.hasAttribute('aria-label')) {
                const text = el.textContent.trim();
                if (text) {
                    el.setAttribute('aria-label', text);
                }
            }
        });

        const gameContainer = document.getElementById('game-container');
        if (gameContainer && !gameContainer.hasAttribute('role')) {
            gameContainer.setAttribute('role', 'region');
            gameContainer.setAttribute('aria-label', 'JARVIS Catcher Spelyta');
        }

        const chatBox = document.getElementById('chat-box');
        if (chatBox && !chatBox.hasAttribute('role')) {
            chatBox.setAttribute('role', 'log');
            chatBox.setAttribute('aria-live', 'polite');
            chatBox.setAttribute('aria-label', 'JARVIS Chatten');
        }
    };

    const announceToScreenReader = (message) => {
        let announcer = document.getElementById('sr-announcer');
        if (!announcer) {
            announcer = document.createElement('div');
            announcer.id = 'sr-announcer';
            announcer.setAttribute('aria-live', 'assertive');
            announcer.classList.add('sr-only');
            document.body.appendChild(announcer);
        }
        announcer.textContent = message;
    };

    window.JARVIS_ACCESSIBILITY = {
        setupAccessibility,
        announceToScreenReader
    };

    setupAccessibility();
});