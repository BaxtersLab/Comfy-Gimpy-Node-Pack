// Models page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    loadLocalModels();

    // Set up search
    document.getElementById('search-btn').addEventListener('click', performSearch);
    document.getElementById('search-query').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
});

async function loadLocalModels() {
    try {
        const response = await fetch('/api/models/list');
        const data = await response.json();

        const container = document.getElementById('local-models-list');

        if (!data.models || Object.keys(data.models).length === 0) {
            container.innerHTML = '<p>No local models found.</p>';
            return;
        }

        let html = '';
        Object.entries(data.models).forEach(([category, models]) => {
            html += `<h3>${category.charAt(0).toUpperCase() + category.slice(1)}</h3>`;
            if (models.length === 0) {
                html += '<p>No models in this category.</p>';
            } else {
                html += '<div class="grid">';
                models.forEach(model => {
                    html += `
                        <div class="card">
                            <h4>${model.name}</h4>
                            <p>${model.description || 'No description'}</p>
                        </div>
                    `;
                });
                html += '</div>';
            }
        });

        container.innerHTML = html;

    } catch (error) {
        console.error('Failed to load local models:', error);
        document.getElementById('local-models-list').innerHTML =
            '<p class="error">Failed to load local models.</p>';
    }
}

async function performSearch() {
    const query = document.getElementById('search-query').value.trim();
    const modelType = document.getElementById('model-type').value;
    const source = document.getElementById('source').value;

    if (!query) {
        showMessage('Please enter a search query', 'error');
        return;
    }

    const resultsContainer = document.getElementById('results-list');
    resultsContainer.innerHTML = '<p>Searching...</p>';

    try {
        // This would call a search API endpoint
        // For now, just show a placeholder
        resultsContainer.innerHTML = `
            <p>Search functionality would be implemented here.</p>
            <p>Query: "${query}", Type: ${modelType}, Source: ${source}</p>
        `;

    } catch (error) {
        console.error('Search failed:', error);
        resultsContainer.innerHTML = '<p class="error">Search failed.</p>';
    }
}