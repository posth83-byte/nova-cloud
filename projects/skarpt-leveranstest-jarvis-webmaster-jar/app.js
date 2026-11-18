document.addEventListener('DOMContentLoaded', () => {
    const taskForm = document.getElementById('taskForm');
    const taskInput = document.getElementById('taskInput');
    const taskList = document.getElementById('taskList');
    const taskCount = document.getElementById('taskCount');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const navMenu = document.getElementById('navMenu');

    let tasks = [
        { id: 1, text: 'Verifiera HTML5 struktur' },
        { id: 2, text: 'Testa CSS responsivitet' },
        { id: 3, text: 'Kör JavaScript logik för uppgifter' }
    ];

    function renderTasks() {
        taskList.innerHTML = '';

        if (tasks.length === 0) {
            const emptyLi = document.createElement('li');
            emptyLi.className = 'task-empty';
            emptyLi.textContent = 'Inga aktiva uppgifter. Lägg till en ovan!';
            taskList.appendChild(emptyLi);
            taskCount.textContent = '0';
            return;
        }

        tasks.forEach((task) => {
            const li = document.createElement('li');
            li.className = 'task-item';

            const span = document.createElement('span');
            span.className = 'task-text';
            span.textContent = task.text;

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'task-delete-btn';
            deleteBtn.textContent = 'Ta bort';
            deleteBtn.setAttribute('aria-label', `Ta bort uppgift: ${task.text}`);

            deleteBtn.addEventListener('click', () => {
                deleteTask(task.id);
            });

            li.appendChild(span);
            li.appendChild(deleteBtn);
            taskList.appendChild(li);
        });

        taskCount.textContent = tasks.length;
    }

    function addTask(text) {
        const newTask = {
            id: Date.now(),
            text: text.trim()
        };
        tasks.push(newTask);
        renderTasks();
    }

    function deleteTask(id) {
        tasks = tasks.filter(task => task.id !== id);
        renderTasks();
    }

    taskForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = taskInput.value;
        if (text.trim() !== '') {
            addTask(text);
            taskInput.value = '';
            taskInput.focus();
        }
    });

    if (mobileMenuBtn && navMenu) {
        mobileMenuBtn.addEventListener('click', () => {
            navMenu.classList.toggle('active');
        });

        navMenu.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navMenu.classList.remove('active');
            });
        });
    }

    renderTasks();
});