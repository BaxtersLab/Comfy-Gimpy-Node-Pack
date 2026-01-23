// Templates page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    loadTemplateCategories();
});

async function loadTemplateCategories() {
    try {
        const response = await fetch('/api/templates/list');
        const data = await response.json();

        const container = document.getElementById('category-list');

        if (!data.data || data.data.length === 0) {
            container.innerHTML = '<p>No template categories found.</p>';
            return;
        }

        let html = '<div class="grid">';
        data.data.forEach(categoryData => {
            const category = categoryData.category;
            html += `
                <div class="card category-card" onclick="loadTemplates('${category.name}')">
                    <h3>${category.display_name}</h3>
                    <p>${category.description}</p>
                    <p><strong>${category.template_count}</strong> templates</p>
                </div>
            `;
        });
        html += '</div>';

        container.innerHTML = html;

    } catch (error) {
        console.error('Failed to load template categories:', error);
        document.getElementById('category-list').innerHTML =
            '<p class="error">Failed to load template categories.</p>';
    }
}

async function loadTemplates(categoryName) {
    try {
        const response = await fetch('/api/templates/list');
        const data = await response.json();

        const categoryData = data.data.find(cat => cat.category.name === categoryName);
        if (!categoryData) {
            document.getElementById('template-grid').innerHTML = '<p>Category not found.</p>';
            return;
        }

        const container = document.getElementById('template-grid');
        const templates = categoryData.templates;

        if (templates.length === 0) {
            container.innerHTML = '<p>No templates in this category.</p>';
            return;
        }

        let html = '<div class="grid">';
        templates.forEach(template => {
            html += `
                <div class="card">
                    <h4>${template.name}</h4>
                    <p>${template.description || 'No description'}</p>
                    <p><em>Tags: ${template.tags.join(', ') || 'None'}</em></p>
                </div>
            `;
        });
        html += '</div>';

        container.innerHTML = html;

    } catch (error) {
        console.error('Failed to load templates:', error);
        document.getElementById('template-grid').innerHTML =
            '<p class="error">Failed to load templates.</p>';
    }
}