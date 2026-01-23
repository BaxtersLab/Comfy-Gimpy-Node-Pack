// Comfy Gimpy Studio Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Load dashboard stats if on home page
    if (document.getElementById('model-count')) {
        loadDashboardStats();
    }
});

async function loadDashboardStats() {
    try {
        // Load models count
        const modelsResponse = await fetch('/api/models/list');
        const modelsData = await modelsResponse.json();
        let modelCount = 0;
        if (modelsData.models) {
            Object.values(modelsData.models).forEach(category => {
                modelCount += category.length;
            });
        }
        document.getElementById('model-count').textContent = modelCount;

        // Load templates count
        const templatesResponse = await fetch('/api/templates/list');
        const templatesData = await templatesResponse.json();
        let templateCount = 0;
        if (templatesData.data) {
            templatesData.data.forEach(cat => {
                templateCount += cat.templates.length;
            });
        }
        document.getElementById('template-count').textContent = templateCount;

        // Load styles count
        const stylesResponse = await fetch('/api/styles/list');
        const stylesData = await stylesResponse.json();
        let styleCount = 0;
        if (stylesData.data) {
            stylesData.data.forEach(cat => {
                styleCount += cat.styles.length;
            });
        }
        document.getElementById('style-count').textContent = styleCount;

        // Load workflows count
        const workflowsResponse = await fetch('/api/workflows/list');
        const workflowsData = await workflowsResponse.json();
        const workflowCount = workflowsData.workflows ? workflowsData.workflows.length : 0;
        document.getElementById('workflow-count').textContent = workflowCount;

    } catch (error) {
        console.error('Failed to load dashboard stats:', error);
        document.getElementById('model-count').textContent = 'Error';
        document.getElementById('template-count').textContent = 'Error';
        document.getElementById('style-count').textContent = 'Error';
        document.getElementById('workflow-count').textContent = 'Error';
    }
}

function showMessage(message, type = 'info') {
    // Remove existing messages
    const existing = document.querySelector('.message');
    if (existing) {
        existing.remove();
    }

    // Create new message
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = message;

    // Add to page
    const main = document.querySelector('main');
    main.insertBefore(messageDiv, main.firstChild);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.remove();
        }
    }, 5000);
}