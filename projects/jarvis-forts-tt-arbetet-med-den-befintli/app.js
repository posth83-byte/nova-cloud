document.addEventListener('DOMContentLoaded', () => {
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const mobileDropdown = document.getElementById('mobile-dropdown');
    const taskInput = document.getElementById('task-input');
    const addTaskBtn = document.getElementById('add-task-btn');
    const taskList = document.getElementById('task-list');
    const taskCountSpan = document.getElementById('task-count');

    function updateTaskCount() {
        const count = taskList.children.length;
        taskCountSpan.textContent = count;
    }

    if (mobileMenuToggle && mobileDropdown) {
        mobileMenuToggle.addEventListener('click', () => {
            mobileDropdown.classList.toggle('hidden');
        });

        const mobileLinks = mobileDropdown.querySelectorAll('a');
        mobileLinks.forEach(link => {
            link.addEventListener('click', () => {
                mobileDropdown.classList.add('hidden');
            });
        });
    }

    function addTask() {
        const taskText = taskInput.value.trim();
        if (taskText === '') return;

        const li = document.createElement('li');
        li.className = 'flex justify-between items-center bg-gray-50 border border-gray-200 px-4 py-3 rounded-lg shadow-sm';

        const span = document.createElement('span');
        span.className = 'text-gray-800 break-all pr-4';
        span.textContent = taskText;

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'task-delete-btn delete-btn';
        deleteBtn.textContent = 'Ta bort';

        deleteBtn.addEventListener('click', () => {
            li.remove();
            updateTaskCount();
        });

        li.appendChild(span);
        li.appendChild(deleteBtn);
        taskList.appendChild(li);

        taskInput.value = '';
        updateTaskCount();
    }

    if (addTaskBtn && taskInput) {
        addTaskBtn.addEventListener('click', addTask);
        taskInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                addTask();
            }
        });
    }

    updateTaskCount();
});