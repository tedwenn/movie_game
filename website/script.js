document.getElementById('submitGuess').addEventListener('click', function() {
    var guess = document.getElementById('guessInput').value;
    sendGuess(guess);
});

function sendGuess(guess) {
    fetch('http://127.0.0.1:5000/submit-guess', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ guess: guess })
    })
    .then(response => response.json())
    .then(data => {
        displayGameStatus(data.game_status);
    })
    .catch((error) => {
        console.error('Error:', error);
    });
}

function displayGameStatus(status) {
    document.getElementById('gameStatus').innerText = JSON.stringify(status, null, 2);
}
