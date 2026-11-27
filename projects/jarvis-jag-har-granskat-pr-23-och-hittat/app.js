document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.getElementById('menu-toggle');
    const navMenu = document.getElementById('nav-menu');
    const taskForm = document.getElementById('task-form');
    const taskInput = document.getElementById('task-input');
    const taskList = document.getElementById('task-list');
    const taskCountSpan = document.getElementById('task-count');

    if (menuToggle && navMenu) {
        menuToggle.addEventListener('click', () => {
            const isExpanded = menuToggle.getAttribute('aria-expanded') === 'true';
            menuToggle.setAttribute('aria-expanded', !isExpanded);
            navMenu.classList.toggle('open');
        });
    }

    const navLinks = document.querySelectorAll('nav a');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            if (navMenu) {
                navMenu.classList.remove('open');
            }
            if (menuToggle) {
                menuToggle.setAttribute('aria-expanded', 'false');
            }
        });
    });

    function updateTaskCount() {
        if (!taskCountSpan || !taskList) return;
        const count = taskList.querySelectorAll('li').length;
        taskCountSpan.textContent = count;
    }

    if (taskForm && taskInput && taskList) {
        taskForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const taskText = taskInput.value.trim();
            if (taskText === '') return;

            const li = document.createElement('li');
            
            const span = document.createElement('span');
            span.textContent = taskText;
            li.appendChild(span);

            const deleteBtn = document.createElement('button');
            deleteBtn.textContent = 'Ta bort';
            deleteBtn.className = 'delete-btn';
            deleteBtn.setAttribute('aria-label', `Ta bort uppgift: ${taskText}`);
            
            deleteBtn.addEventListener('click', () => {
                li.remove();
                updateTaskCount();
            });

            li.appendChild(deleteBtn);
            taskList.appendChild(li);

            taskInput.value = '';
            updateTaskCount();
        });
    }

    const existingDeleteButtons = document.querySelectorAll('.delete-btn');
    existingDeleteButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const li = e.target.closest('li');
            if (li) {
                li.remove();
                updateTaskCount();
            }
        });
    });

    updateTaskCount();
});