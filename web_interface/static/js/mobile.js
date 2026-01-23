// mobile.js - Mobile Companion Interface

class MobileInterface {
    constructor() {
        this.devices = [];
        this.currentSession = null;
        this.previewActive = false;

        this.init();
    }

    init() {
        this.bindEvents();
        this.loadDevices();
        this.updateStatus();
    }

    bindEvents() {
        // Pairing
        document.getElementById('generate-qr').addEventListener('click', () => this.generateQR());

        // Devices
        document.getElementById('refresh-devices').addEventListener('click', () => this.loadDevices());

        // Sync
        document.getElementById('push-image').addEventListener('click', () => this.pushImage());
        document.getElementById('push-workflow').addEventListener('click', () => this.pushWorkflow());
        document.getElementById('pull-assets').addEventListener('click', () => this.pullAssets());

        // Remote control
        document.getElementById('start-session').addEventListener('click', () => this.startRemoteSession());
        document.getElementById('execute-remote').addEventListener('click', () => this.executeRemoteWorkflow());

        // Preview
        document.getElementById('start-preview').addEventListener('click', () => this.startPreview());
        document.getElementById('stop-preview').addEventListener('click', () => this.stopPreview());
        document.getElementById('preview-quality').addEventListener('change', (e) => this.setPreviewQuality(e.target.value));
    }

    async generateQR() {
        try {
            const response = await fetch('/api/mobile/qr');
            const data = await response.json();

            if (data.qr_data) {
                document.getElementById('qr-code').src = data.qr_data;
                document.getElementById('pairing-token').textContent = `Token: ${data.pairing_token}`;
                document.getElementById('qr-container').style.display = 'block';
            } else {
                this.showError('Failed to generate QR code');
            }
        } catch (error) {
            this.showError('Error generating QR code: ' + error.message);
        }
    }

    async loadDevices() {
        try {
            const response = await fetch('/api/mobile/devices');
            const data = await response.json();

            this.devices = data.devices || [];
            this.renderDevices();
        } catch (error) {
            this.showError('Error loading devices: ' + error.message);
        }
    }

    renderDevices() {
        const container = document.getElementById('devices-list');

        if (this.devices.length === 0) {
            container.innerHTML = '<p>No paired devices found</p>';
            return;
        }

        const html = this.devices.map(device => `
            <div class="device-item">
                <h4>${device.info.name || 'Unknown Device'}</h4>
                <p>Status: ${device.status}</p>
                <p>Last seen: ${new Date(device.info.last_seen * 1000).toLocaleString()}</p>
                <button class="btn btn-small" onclick="mobileInterface.selectDevice('${device.device_id}')">
                    Select
                </button>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    selectDevice(deviceId) {
        this.selectedDevice = deviceId;
        // Update UI to show selected device
        document.querySelectorAll('.device-item').forEach(item => {
            item.classList.remove('selected');
        });
        event.target.closest('.device-item').classList.add('selected');
    }

    async pushImage() {
        if (!this.selectedDevice) {
            this.showError('Please select a device first');
            return;
        }

        try {
            const response = await fetch(`/api/mobile/push/${this.selectedDevice}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    asset_path: '/path/to/current/image.png', // This would come from GIMP
                    asset_type: 'image'
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                this.showSuccess('Image push initiated');
            } else {
                this.showError('Failed to push image: ' + result.error);
            }
        } catch (error) {
            this.showError('Error pushing image: ' + error.message);
        }
    }

    async pushWorkflow() {
        if (!this.selectedDevice) {
            this.showError('Please select a device first');
            return;
        }

        try {
            const response = await fetch(`/api/mobile/push/${this.selectedDevice}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'workflow',
                    workflow_name: 'current_workflow'
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                this.showSuccess('Workflow push initiated');
            } else {
                this.showError('Failed to push workflow: ' + result.error);
            }
        } catch (error) {
            this.showError('Error pushing workflow: ' + error.message);
        }
    }

    async pullAssets() {
        if (!this.selectedDevice) {
            this.showError('Please select a device first');
            return;
        }

        try {
            const response = await fetch(`/api/mobile/pull/${this.selectedDevice}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'asset',
                    asset_type: 'image'
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                this.showSuccess('Asset pull initiated');
            } else {
                this.showError('Failed to pull assets: ' + result.error);
            }
        } catch (error) {
            this.showError('Error pulling assets: ' + error.message);
        }
    }

    async startRemoteSession() {
        if (!this.selectedDevice) {
            this.showError('Please select a device first');
            return;
        }

        try {
            const response = await fetch(`/api/mobile/remote/${this.selectedDevice}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    command: 'start_session',
                    session_type: 'full'
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                this.currentSession = result.session_id;
                this.showSuccess('Remote session started');
                this.updateStatus();
            } else {
                this.showError('Failed to start remote session: ' + result.error);
            }
        } catch (error) {
            this.showError('Error starting remote session: ' + error.message);
        }
    }

    async executeRemoteWorkflow() {
        if (!this.currentSession) {
            this.showError('No active remote session');
            return;
        }

        try {
            const response = await fetch(`/api/mobile/remote/${this.selectedDevice}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: this.currentSession,
                    command: 'execute_workflow',
                    parameters: { workflow_id: 'selected_workflow' }
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                this.showSuccess('Remote workflow execution started');
            } else {
                this.showError('Failed to execute remote workflow: ' + result.error);
            }
        } catch (error) {
            this.showError('Error executing remote workflow: ' + error.message);
        }
    }

    async startPreview() {
        try {
            const response = await fetch('/api/mobile/preview/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    preview_id: 'main_preview',
                    preview_type: 'image'
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                this.previewActive = true;
                this.showSuccess('Preview stream started');
                this.updateStatus();
            } else {
                this.showError('Failed to start preview: ' + result.error);
            }
        } catch (error) {
            this.showError('Error starting preview: ' + error.message);
        }
    }

    async stopPreview() {
        try {
            const response = await fetch('/api/mobile/preview/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    preview_id: 'main_preview'
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                this.previewActive = false;
                this.showSuccess('Preview stream stopped');
                this.updateStatus();
            } else {
                this.showError('Failed to stop preview: ' + result.error);
            }
        } catch (error) {
            this.showError('Error stopping preview: ' + error.message);
        }
    }

    async setPreviewQuality(quality) {
        try {
            const response = await fetch('/api/mobile/preview/stop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    preview_id: 'main_preview',
                    quality: quality
                })
            });

            const result = await response.json();
            if (result.status === 'success') {
                this.showSuccess('Preview quality updated');
            }
        } catch (error) {
            this.showError('Error updating preview quality: ' + error.message);
        }
    }

    async updateStatus() {
        try {
            const response = await fetch('/api/mobile/status');
            const data = await response.json();

            // Update sync status
            const syncStatus = document.getElementById('sync-status');
            syncStatus.innerHTML = `
                <p>Active pushes: ${data.status.pending_pushes}</p>
                <p>Active pulls: ${data.status.pending_pulls}</p>
            `;

            // Update remote status
            const remoteStatus = document.getElementById('remote-status');
            remoteStatus.innerHTML = `
                <p>Active sessions: ${data.status.active_remote_sessions}</p>
                ${this.currentSession ? `<p>Current session: ${this.currentSession}</p>` : ''}
            `;

            // Update preview status
            const previewStatus = document.getElementById('preview-status');
            previewStatus.innerHTML = `
                <p>Status: ${this.previewActive ? 'Active' : 'Inactive'}</p>
                <p>Active streams: ${data.status.active_previews}</p>
            `;

        } catch (error) {
            console.error('Error updating status:', error);
        }
    }

    showSuccess(message) {
        this.showMessage(message, 'success');
    }

    showError(message) {
        this.showMessage(message, 'error');
    }

    showMessage(message, type) {
        // Simple notification - could be enhanced with a proper notification system
        alert(`${type.toUpperCase()}: ${message}`);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mobileInterface = new MobileInterface();
});