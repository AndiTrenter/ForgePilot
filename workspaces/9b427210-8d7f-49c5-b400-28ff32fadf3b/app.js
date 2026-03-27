document.getElementById('greetButton').addEventListener('click', function() {
    const name = document.getElementById('nameInput').value;
    const greetingMessage = `Hallo ${name}!`;
    document.getElementById('greetingMessage').textContent = greetingMessage;
});