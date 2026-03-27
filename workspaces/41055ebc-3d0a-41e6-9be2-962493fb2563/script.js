document.addEventListener('DOMContentLoaded', function () {
    const display = document.getElementById('display');
    const buttons = document.querySelectorAll('#buttons button');
    let currentInput = '';
    let operator = '';
    let operand1 = null;
    let operand2 = null;

    buttons.forEach(button => {
        button.addEventListener('click', () => {
            const value = button.getAttribute('data-value');

            if (!isNaN(value) || value === '.') {
                currentInput += value;
                display.value = currentInput;
            } else if (value === 'C') {
                currentInput = '';
                operator = '';
                operand1 = null;
                operand2 = null;
                display.value = '';
            } else if (value === '=') {
                if (operand1 !== null && currentInput !== '') {
                    operand2 = parseFloat(currentInput);
                    let result;
                    switch (operator) {
                        case '+':
                            result = operand1 + operand2;
                            break;
                        case '-':
                            result = operand1 - operand2;
                            break;
                        case '*':
                            result = operand1 * operand2;
                            break;
                        case '/':
                            result = operand1 / operand2;
                            break;
                    }
                    display.value = result;
                    currentInput = '' + result;
                    operand1 = result;
                }
            } else if (value === '%') {
                if (currentInput !== '') {
                    currentInput = parseFloat(currentInput) / 100;
                    display.value = currentInput;
                }
            } else {
                if (currentInput !== '') {
                    operand1 = parseFloat(currentInput);
                    operator = value;
                    currentInput = '';
                }
            }
        });
    });
});