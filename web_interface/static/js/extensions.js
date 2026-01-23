// web_interface/static/js/extensions.js

/**
 * Extensions Management UI for Comfy Gimpy Studio
 */

class ExtensionsManager {
    constructor() {
        this.currentTab = 'installed';
        this.extensions = {};
        this.marketplaceExtensions = [];
        this.settings = {};

        this.init();
    }

    init() {
        this.bindEvents();
        this.loadExtensions();
        this.loadSettings();
    }

    bindEvents() {
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadExtensions();
        });

        // Settings button
        document.getElementById('settings-btn').addEventListener('click', () => {
            this.showSettingsModal();
        });

        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                this.closeModals();
            });
        });

        // Marketplace filters
        document.getElementById('search-input').addEventListener('input', () => {
            this.filterMarketplace();
        });

        document.getElementById('category-filter').addEventListener('change', () => {
            this.filterMarketplace();
        });

        document.getElementById('sort-filter').addEventListener('change', () => {
            this.filterMarketplace();
        });

        // Settings modal
        document.getElementById('save-settings-btn').addEventListener('click', () => {
            this.saveSettings();
        });

        // Click outside modal to close
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModals();
                }
            });
        });
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.currentTab = tabName;

        if (tabName === 'marketplace' && this.marketplaceExtensions.length === 0) {
            this.loadMarketplace();
        }
    }

    async loadExtensions() {
        try {
            this.showLoading('installed-extensions');

            const response = await fetch('/api/extensions/');
            const data = await response.json();

            if (data.success) {
                this.extensions = data.extensions;
                this.renderInstalledExtensions();
            } else {
                this.showError('Failed to load extensions: ' + data.error);
            }
        } catch (error) {
            this.showError('Failed to load extensions: ' + error.message);
        } finally {
            this.hideLoading('installed-extensions');
        }
    }

    async loadMarketplace() {
        try {
            this.showLoading('marketplace-extensions');

            const response = await fetch('/api/extensions/marketplace');
            const data = await response.json();

            if (data.success) {
                this.marketplaceExtensions = data.extensions;
                this.renderMarketplaceExtensions();
            } else {
                this.showError('Failed to load marketplace: ' + data.error);
            }
        } catch (error) {
            this.showError('Failed to load marketplace: ' + error.message);
        } finally {
            this.hideLoading('marketplace-extensions');
        }
    }

    async loadSettings() {
        try {
            const response = await fetch('/api/extensions/settings');
            const data = await response.json();

            if (data.success) {
                this.settings = data.settings;
                this.populateSettingsModal();
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }

    renderInstalledExtensions() {
        const container = document.getElementById('installed-extensions');
        container.innerHTML = '';

        Object.entries(this.extensions).forEach(([extId, ext]) => {
            const card = this.createExtensionCard(ext, false);
            container.appendChild(card);
        });

        if (Object.keys(this.extensions).length === 0) {
            container.innerHTML = '<div class="empty-state">No extensions installed</div>';
        }
    }

    renderMarketplaceExtensions() {
        const container = document.getElementById('marketplace-extensions');
        container.innerHTML = '';

        this.marketplaceExtensions.forEach(ext => {
            const card = this.createExtensionCard(ext, true);
            container.appendChild(card);
        });

        if (this.marketplaceExtensions.length === 0) {
            container.innerHTML = '<div class="empty-state">No extensions found</div>';
        }
    }

    createExtensionCard(extension, isMarketplace = false) {
        const card = document.createElement('div');
        card.className = 'extension-card';
        card.dataset.extensionId = extension.extension_id || extension.id;

        const statusClass = extension.enabled ? 'status-enabled' : 'status-disabled';
        const statusText = extension.enabled ? 'Enabled' : 'Disabled';

        card.innerHTML = `
            <div class="extension-header">
                <div class="extension-icon">${this.getExtensionIcon(extension)}</div>
                <div class="extension-info">
                    <h3 class="extension-name">${extension.name}</h3>
                    <p class="extension-author">by ${extension.author}</p>
                    <p class="extension-description">${extension.description}</p>
                </div>
            </div>
            <div class="extension-tags">
                ${extension.tags ? extension.tags.map(tag => `<span class="extension-tag">${tag}</span>`).join('') : ''}
            </div>
            <div class="extension-meta">
                <div>
                    <span class="extension-status ${statusClass}">${statusText}</span>
                    ${extension.version ? `<span>v${extension.version}</span>` : ''}
                </div>
                <div class="extension-actions">
                    ${this.getActionButtons(extension, isMarketplace)}
                </div>
            </div>
        `;

        // Bind events
        card.addEventListener('click', (e) => {
            if (!e.target.closest('.extension-actions')) {
                this.showExtensionDetails(extension, isMarketplace);
            }
        });

        return card;
    }

    getExtensionIcon(extension) {
        // Return appropriate emoji based on extension type
        const tags = extension.tags || [];
        if (tags.includes('workflows')) return '⚡';
        if (tags.includes('ui')) return '🎨';
        if (tags.includes('assets')) return '📦';
        if (tags.includes('copywriting')) return '✍️';
        if (tags.includes('brand')) return '🏷️';
        if (tags.includes('layout')) return '📐';
        return '🔌';
    }

    getActionButtons(extension, isMarketplace) {
        if (isMarketplace) {
            return `
                <button class="btn-primary install-btn" data-extension-id="${extension.id}">
                    <span class="icon">⬇️</span> Install
                </button>
            `;
        } else {
            const toggleText = extension.enabled ? 'Disable' : 'Enable';
            const toggleClass = extension.enabled ? 'btn-secondary' : 'btn-success';

            return `
                <button class="btn-primary reload-btn" data-extension-id="${extension.extension_id}">
                    <span class="icon">🔄</span> Reload
                </button>
                <button class="${toggleClass} toggle-btn" data-extension-id="${extension.extension_id}">
                    <span class="icon">${extension.enabled ? '⏸️' : '▶️'}</span> ${toggleText}
                </button>
            `;
        }
    }

    filterMarketplace() {
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        const category = document.getElementById('category-filter').value;
        const sortBy = document.getElementById('sort-filter').value;

        let filtered = this.marketplaceExtensions.filter(ext => {
            const matchesSearch = ext.name.toLowerCase().includes(searchTerm) ||
                                ext.description.toLowerCase().includes(searchTerm) ||
                                ext.author.toLowerCase().includes(searchTerm);

            const matchesCategory = !category || (ext.tags && ext.tags.includes(category));

            return matchesSearch && matchesCategory;
        });

        // Sort
        filtered.sort((a, b) => {
            switch (sortBy) {
                case 'downloads':
                    return (b.downloads || 0) - (a.downloads || 0);
                case 'rating':
                    return (b.rating || 0) - (a.rating || 0);
                case 'recent':
                    return new Date(b.created_at || 0) - new Date(a.created_at || 0);
                case 'name':
                    return a.name.localeCompare(b.name);
                default:
                    return 0;
            }
        });

        // Re-render
        const container = document.getElementById('marketplace-extensions');
        container.innerHTML = '';
        filtered.forEach(ext => {
            const card = this.createExtensionCard(ext, true);
            container.appendChild(card);
        });
    }

    async showExtensionDetails(extension, isMarketplace) {
        const modal = document.getElementById('extension-modal');
        const title = document.getElementById('modal-title');
        const body = document.getElementById('modal-body');
        const actionBtn = document.getElementById('modal-action-btn');

        title.textContent = extension.name;

        body.innerHTML = `
            <div class="extension-details">
                <p><strong>Author:</strong> ${extension.author}</p>
                <p><strong>Version:</strong> ${extension.version || 'N/A'}</p>
                <p><strong>Description:</strong> ${extension.description}</p>
                ${extension.tags ? `<p><strong>Tags:</strong> ${extension.tags.join(', ')}</p>` : ''}
                ${extension.price ? `<p><strong>Price:</strong> $${extension.price}</p>` : ''}
                ${extension.downloads ? `<p><strong>Downloads:</strong> ${extension.downloads}</p>` : ''}
                ${extension.repository ? `<p><strong>Repository:</strong> <a href="${extension.repository}" target="_blank">${extension.repository}</a></p>` : ''}
                ${extension.homepage ? `<p><strong>Homepage:</strong> <a href="${extension.homepage}" target="_blank">${extension.homepage}</a></p>` : ''}
            </div>
        `;

        if (isMarketplace) {
            actionBtn.textContent = 'Install';
            actionBtn.onclick = () => this.installFromMarketplace(extension.id);
        } else {
            actionBtn.textContent = extension.enabled ? 'Disable' : 'Enable';
            actionBtn.onclick = () => this.toggleExtension(extension.extension_id);
        }

        modal.style.display = 'block';
    }

    showSettingsModal() {
        this.populateSettingsModal();
        document.getElementById('settings-modal').style.display = 'block';
    }

    populateSettingsModal() {
        document.getElementById('auto-update-toggle').checked = this.settings.auto_update || false;
        document.getElementById('hot-reload-toggle').checked = this.settings.hot_reload || false;
        document.getElementById('max-extensions-input').value = this.settings.max_extensions || 50;

        // Populate trusted sources
        const sourcesList = document.getElementById('trusted-sources-list');
        sourcesList.innerHTML = '';
        (this.settings.trusted_sources || []).forEach(source => {
            const sourceDiv = document.createElement('div');
            sourceDiv.className = 'trusted-source-item';
            sourceDiv.innerHTML = `
                <span>${source}</span>
                <button class="btn-danger remove-source" data-source="${source}">Remove</button>
            `;
            sourcesList.appendChild(sourceDiv);
        });
    }

    async saveSettings() {
        const settings = {
            auto_update: document.getElementById('auto-update-toggle').checked,
            hot_reload: document.getElementById('hot-reload-toggle').checked,
            max_extensions: parseInt(document.getElementById('max-extensions-input').value),
            trusted_sources: Array.from(document.querySelectorAll('.trusted-source-item span'))
                .map(span => span.textContent)
        };

        try {
            const response = await fetch('/api/extensions/settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });

            const data = await response.json();

            if (data.success) {
                this.settings = settings;
                this.closeModals();
                this.showNotification('Settings saved successfully', 'success');
            } else {
                this.showError('Failed to save settings: ' + data.error);
            }
        } catch (error) {
            this.showError('Failed to save settings: ' + error.message);
        }
    }

    async toggleExtension(extensionId) {
        const extension = this.extensions[extensionId];
        const action = extension.enabled ? 'disable' : 'enable';

        try {
            const response = await fetch(`/api/extensions/${extensionId}/${action}`, {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                extension.enabled = !extension.enabled;
                this.renderInstalledExtensions();
                this.closeModals();
                this.showNotification(`Extension ${action}d successfully`, 'success');
            } else {
                this.showError(`Failed to ${action} extension: ` + data.error);
            }
        } catch (error) {
            this.showError(`Failed to ${action} extension: ` + error.message);
        }
    }

    async installFromMarketplace(extensionId) {
        try {
            const response = await fetch(`/api/extensions/marketplace/${extensionId}/install`, {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.closeModals();
                this.showNotification('Extension installed successfully', 'success');
                this.loadExtensions(); // Refresh installed extensions
            } else {
                this.showError('Failed to install extension: ' + data.error);
            }
        } catch (error) {
            this.showError('Failed to install extension: ' + error.message);
        }
    }

    closeModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
    }

    showLoading(containerId) {
        const container = document.getElementById(containerId);
        container.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                Loading...
            </div>
        `;
    }

    hideLoading(containerId) {
        // Loading state will be replaced when content is rendered
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        // Simple notification - in a real app you'd use a proper notification system
        alert(`${type.toUpperCase()}: ${message}`);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ExtensionsManager();
});