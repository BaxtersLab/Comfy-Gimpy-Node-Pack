// Workflows page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    loadWorkflows();
});

async function loadWorkflows() {
    try {
        const response = await fetch('/api/workflows/list');
        const data = await response.json();

        const container = document.getElementById('workflow-list');

        if (!data.workflows || data.workflows.length === 0) {
            container.innerHTML = '<p>No workflows found.</p>';
            return;
        }

        let html = '<div class="grid">';
        data.workflows.forEach(workflow => {
            html += `
                <div class="card">
                    <h3>${workflow.name}</h3>
                    <p>${workflow.description}</p>
                    <p><em>Category: ${workflow.category}</em></p>
                    <p><strong>Inputs:</strong> ${workflow.inputs.join(', ')}</p>
                    <p><strong>Outputs:</strong> ${workflow.outputs.join(', ')}</p>
                </div>
            `;
        });
        html += '</div>';

        container.innerHTML = html;

    } catch (error) {
        console.error('Failed to load workflows:', error);
        document.getElementById('workflow-list').innerHTML =
            '<p class="error">Failed to load workflows.</p>';
    }
}