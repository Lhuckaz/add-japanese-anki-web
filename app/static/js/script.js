const dropdown = document.querySelector('.languages');
const selected = dropdown.querySelector('.selected');
const optionsContainer = dropdown.querySelector('.options');
const optionsList = optionsContainer.querySelectorAll('li');
const hiddenInput = document.getElementById('dropdownValue');
const wordInput = document.getElementById('word');
const form = document.getElementById('language');
const resultBox = document.getElementById('result');

function showMessage(type, message) {
    resultBox.classList.remove('success', 'error');
    resultBox.classList.add(type);
    resultBox.textContent = message;

    setTimeout(() => {
        resultBox.classList.remove('success', 'error');
        resultBox.textContent = '';
    }, 5000);
}

dropdown.addEventListener('click', () => {
    dropdown.classList.toggle('open');
});

optionsList.forEach(option => {
    option.addEventListener('click', () => {
        selected.textContent = option.textContent;
        selected.dataset.value = option.dataset.value;
        hiddenInput.value = option.dataset.value;
    });
});

document.addEventListener('click', (e) => {
    if (!dropdown.contains(e.target)) {
        dropdown.classList.remove('open');
    }
});

dropdown.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        dropdown.classList.toggle('open');
    }
    if (e.key === 'Escape') {
        dropdown.classList.remove('open');
    }
});


form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const value = hiddenInput.value;
    const word = wordInput.value;

    try {
        const res = await fetch('/api/addnote', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                word: word,
                dropdownValue: value
            })
        });

        const result = await res.json();
        if (!res.ok) {
            console.error(result?.error || 'Unknown error');
            showMessage('error', 'Failed to add');
            return;
        }
        showMessage('success', result.message || 'Note added!');
    } catch (err) {
        console.error(err);
        showMessage('error', 'Error submitting note');
    }
});