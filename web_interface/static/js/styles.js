// Styles page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    loadStyleCategories();
});

async function loadStyleCategories() {
    try {
        const response = await fetch('/api/styles/list');
        const data = await response.json();

        const container = document.getElementById('category-list');

        if (!data.data || data.data.length === 0) {
            container.innerHTML = '<p>No style categories found.</p>';
            return;
        }

        let html = '<div class="grid">';
        data.data.forEach(categoryData => {
            const category = categoryData.category;
            html += `
                <div class="card category-card" onclick="loadStyles('${category.name}')">
                    <h3>${category.display_name}</h3>
                    <p>${category.description}</p>
                    <p><strong>${category.style_count}</strong> styles</p>
                </div>
            `;
        });
        html += '</div>';

        container.innerHTML = html;

    } catch (error) {
        console.error('Failed to load style categories:', error);
        document.getElementById('category-list').innerHTML =
            '<p class="error">Failed to load style categories.</p>';
    }
}

async function loadStyles(categoryName) {
    try {
        const response = await fetch('/api/styles/list');
        const data = await response.json();

        const categoryData = data.data.find(cat => cat.category.name === categoryName);
        if (!categoryData) {
            document.getElementById('style-grid').innerHTML = '<p>Category not found.</p>';
            return;
        }

        const container = document.getElementById('style-grid');
        const styles = categoryData.styles;

        if (styles.length === 0) {
            container.innerHTML = '<p>No styles in this category.</p>';
            return;
        }

        let html = '<div class="grid">';
        styles.forEach(style => {
            html += `
                <div class="card">
                    <h4>${style.name}</h4>
                    <p>${style.description || 'No description'}</p>
                    <p><em>Weight: ${style.default_weight}, Tags: ${style.tags.join(', ') || 'None'}</em></p>
                </div>
            `;
        });
        html += '</div>';

        container.innerHTML = html;

    } catch (error) {
        console.error('Failed to load styles:', error);
        document.getElementById('style-grid').innerHTML =
            '<p class="error">Failed to load styles.</p>';
    }
}