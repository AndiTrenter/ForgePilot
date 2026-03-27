document.addEventListener('DOMContentLoaded', (event) => {
    const addButton = document.getElementById('add-todo');
    const todoInput = document.getElementById('todo-input');
    const todoList = document.getElementById('todo-list');

    addButton.addEventListener('click', () => {
        const todoText = todoInput.value.trim();
        if (todoText !== '') {
            addTodo(todoText);
            todoInput.value = '';
        }
    });

    function addTodo(text) {
        const li = document.createElement('li');
        li.textContent = text;

        const completeButton = document.createElement('button');
        completeButton.textContent = 'Erledigt';
        completeButton.addEventListener('click', () => {
            li.classList.toggle('completed');
        });

        const deleteButton = document.createElement('button');
        deleteButton.textContent = 'Löschen';
        deleteButton.addEventListener('click', () => {
            todoList.removeChild(li);
        });

        li.appendChild(completeButton);
        li.appendChild(deleteButton);
        todoList.appendChild(li);
    }
});