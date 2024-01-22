async function searchMovies() {
    const apiKey = 'YOUR_API_KEY'; // figure out a safer way to store this
    const query = document.getElementById('searchQuery').value;
    const url = `https://api.themoviedb.org/3/search/movie?api_key=${apiKey}&query=${encodeURIComponent(query)}`;

    try {
        const response = await fetch(url);
        const data = await response.json();
        displayResults(data);
    } catch (error) {
        console.error('Error:', error);
    }
}

function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = ''; // Clear previous results

    if (data.results && data.results.length > 0) {
        data.results.forEach(movie => {
            const div = document.createElement('div');
            div.textContent = `${movie.title} (${movie.release_date})`;
            resultsDiv.appendChild(div);
        });
    } else {
        resultsDiv.innerHTML = 'No results found';
    }
}
