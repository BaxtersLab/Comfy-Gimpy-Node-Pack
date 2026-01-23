// Settings page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    loadSettings();

    // Set up form submission
    document.getElementById('settings-form').addEventListener('submit', saveSettings);
});

async function loadSettings() {
    try {
        const response = await fetch('/api/settings/get');
        const data = await response.json();

        if (data.settings) {
            document.getElementById('comfyui-host').value = data.settings.comfyui_host || '';
            document.getElementById('comfyui-port').value = data.settings.comfyui_port || '';
            document.getElementById('bridge-host').value = data.settings.bridge_host || '';
            document.getElementById('bridge-port').value = data.settings.bridge_port || '';
            document.getElementById('log-level').value = data.settings.log_level || 'INFO';
        }

        // Load directory info
        loadDirectoryInfo(data.settings);

    } catch (error) {
        console.error('Failed to load settings:', error);
        showMessage('Failed to load settings', 'error');
    }
}

function loadDirectoryInfo(settings) {
    const container = document.getElementById('directory-info');

    if (!settings) {
        container.innerHTML = '<p>No settings available.</p>';
        return;
    }

    let html = '<div class="grid">';
    html += `<div class="card"><h4>Workflows Directory</h4><p>${settings.workflows_dir || 'Not set'}</p></div>`;
    html += `<div class="card"><h4>Templates Directory</h4><p>${settings.templates_dir || 'Not set'}</p></div>`;
    html += `<div class="card"><h4>Styles Directory</h4><p>${settings.styles_dir || 'Not set'}</p></div>`;
    html += `<div class="card"><h4>Temp Directory</h4><p>${settings.temp_dir || 'Not set'}</p></div>`;
    html += '</div>';

    container.innerHTML = html;
}

async function saveSettings(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    const settings = Object.fromEntries(formData.entries());

    try {
        const response = await fetch('/api/settings/set', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        });

        const result = await response.json();

        if (response.ok) {
            showMessage('Settings saved successfully', 'success');
        } else {
            showMessage(`Failed to save settings: ${result.error}`, 'error');
        }

    } catch (error) {
        console.error('Failed to save settings:', error);
        showMessage('Failed to save settings', 'error');
    }
}