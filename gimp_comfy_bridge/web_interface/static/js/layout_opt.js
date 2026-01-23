/**
 * Layout Optimization UI JavaScript
 */

class LayoutOptimizerUI {
    constructor() {
        this.currentLayout = null;
        this.analysisResults = null;
        this.optimizationResults = null;
        this.variants = null;

        this.initializeElements();
        this.setupEventListeners();
        this.loadOverlayTypes();
        this.loadStrategies();
    }

    initializeElements() {
        // Upload elements
        this.uploadArea = document.getElementById('uploadArea');
        this.uploadBtn = document.getElementById('uploadBtn');
        this.layoutFile = document.getElementById('layoutFile');

        // Analysis elements
        this.analysisSection = document.getElementById('analysisSection');
        this.analyzeBtn = document.getElementById('analyzeBtn');
        this.generateOverlays = document.getElementById('generateOverlays');
        this.analysisResults = document.getElementById('analysisResults');
        this.overallScore = document.getElementById('overallScore');
        this.scoreBreakdown = document.getElementById('scoreBreakdown');
        this.violationsContainer = document.getElementById('violationsContainer');
        this.recommendationsList = document.getElementById('recommendationsList');

        // Optimization elements
        this.optimizationSection = document.getElementById('optimizationSection');
        this.optimizationLevel = document.getElementById('optimizationLevel');
        this.overlayCheckboxes = document.getElementById('overlayCheckboxes');
        this.optimizeBtn = document.getElementById('optimizeBtn');
        this.optimizationResults = document.getElementById('optimizationResults');
        this.improvementScore = document.getElementById('improvementScore');
        this.actionsApplied = document.getElementById('actionsApplied');
        this.layoutSvg = document.getElementById('layoutSvg');
        this.toggleOverlays = document.getElementById('toggleOverlays');
        this.overlayLegend = document.getElementById('overlayLegend');

        // Variants elements
        this.variantsSection = document.getElementById('variantsSection');
        this.strategyCheckboxes = document.getElementById('strategyCheckboxes');
        this.variantsCount = document.getElementById('variantsCount');
        this.generateVariantsBtn = document.getElementById('generateVariantsBtn');
        this.variantsResults = document.getElementById('variantsResults');
        this.variantsGrid = document.getElementById('variantsGrid');

        // Loading and error elements
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.loadingText = document.getElementById('loadingText');
        this.errorMessage = document.getElementById('errorMessage');
    }

    setupEventListeners() {
        // Upload events
        this.uploadArea.addEventListener('click', () => this.layoutFile.click());
        this.uploadBtn.addEventListener('click', () => this.layoutFile.click());
        this.layoutFile.addEventListener('change', (e) => this.handleFileUpload(e));

        // Drag and drop
        this.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.uploadArea.classList.add('dragover');
        });
        this.uploadArea.addEventListener('dragleave', () => {
            this.uploadArea.classList.remove('dragover');
        });
        this.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFile(files[0]);
            }
        });

        // Analysis events
        this.analyzeBtn.addEventListener('click', () => this.analyzeLayout());

        // Optimization events
        this.optimizeBtn.addEventListener('click', () => this.optimizeLayout());
        this.toggleOverlays.addEventListener('click', () => this.toggleOverlaysVisibility());

        // Variants events
        this.generateVariantsBtn.addEventListener('click', () => this.generateVariants());
    }

    async loadOverlayTypes() {
        try {
            const response = await fetch('/api/layout-opt/overlay-types');
            const data = await response.json();

            this.overlayCheckboxes.innerHTML = '';
            data.overlay_types.forEach(type => {
                const checkbox = document.createElement('div');
                checkbox.className = 'checkbox-item';
                checkbox.innerHTML = `
                    <input type="checkbox" id="overlay-${type}" value="${type}" checked>
                    <label for="overlay-${type}">${type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</label>
                `;
                this.overlayCheckboxes.appendChild(checkbox);
            });
        } catch (error) {
            console.error('Failed to load overlay types:', error);
        }
    }

    async loadStrategies() {
        try {
            const response = await fetch('/api/layout-opt/strategies');
            const data = await response.json();

            this.strategyCheckboxes.innerHTML = '';
            data.strategies.forEach(strategy => {
                const checkbox = document.createElement('div');
                checkbox.className = 'checkbox-item';
                checkbox.innerHTML = `
                    <input type="checkbox" id="strategy-${strategy}" value="${strategy}" checked>
                    <label for="strategy-${strategy}">${strategy.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</label>
                `;
                this.strategyCheckboxes.appendChild(checkbox);
            });
        } catch (error) {
            console.error('Failed to load strategies:', error);
        }
    }

    handleFileUpload(event) {
        const file = event.target.files[0];
        if (file) {
            this.handleFile(file);
        }
    }

    async handleFile(file) {
        try {
            const text = await file.text();
            let layoutData;

            if (file.name.endsWith('.json')) {
                layoutData = JSON.parse(text);
            } else if (file.name.endsWith('.yaml') || file.name.endsWith('.yml')) {
                // Simple YAML parsing (would need a proper YAML library)
                layoutData = this.parseYAML(text);
            } else {
                throw new Error('Unsupported file format');
            }

            this.currentLayout = layoutData;
            this.showAnalysisSection();

        } catch (error) {
            this.showError(`Failed to parse layout file: ${error.message}`);
        }
    }

    parseYAML(text) {
        // Very basic YAML parser for simple structures
        const lines = text.split('\n');
        const result = {};

        let currentObject = result;
        let indentStack = [result];

        lines.forEach(line => {
            if (!line.trim() || line.trim().startsWith('#')) return;

            const indent = line.length - line.trimStart().length;
            const trimmed = line.trim();

            // Adjust indent stack
            while (indentStack.length > 1 && indent <= this.getIndentLevel(indentStack.length - 1)) {
                indentStack.pop();
            }

            currentObject = indentStack[indentStack.length - 1];

            if (trimmed.includes(':')) {
                const [key, ...valueParts] = trimmed.split(':');
                const keyTrimmed = key.trim();
                const value = valueParts.join(':').trim();

                if (value) {
                    // Simple value
                    currentObject[keyTrimmed] = this.parseYAMLValue(value);
                } else {
                    // Object
                    const newObject = {};
                    currentObject[keyTrimmed] = newObject;
                    indentStack.push(newObject);
                }
            }
        });

        return result;
    }

    parseYAMLValue(value) {
        if (value === 'null' || value === '~') return null;
        if (value === 'true') return true;
        if (value === 'false') return false;
        if (/^\d+$/.test(value)) return parseInt(value);
        if (/^\d+\.\d+$/.test(value)) return parseFloat(value);
        if (value.startsWith('"') && value.endsWith('"')) return value.slice(1, -1);
        if (value.startsWith("'") && value.endsWith("'")) return value.slice(1, -1);
        return value;
    }

    getIndentLevel(depth) {
        return (depth - 1) * 2; // Assuming 2 spaces per indent
    }

    showAnalysisSection() {
        this.analysisSection.style.display = 'block';
        this.optimizationSection.style.display = 'none';
        this.variantsSection.style.display = 'none';
    }

    async analyzeLayout() {
        if (!this.currentLayout) {
            this.showError('No layout loaded');
            return;
        }

        this.showLoading('Analyzing layout...');

        try {
            const requestData = {
                elements: this.currentLayout.elements || [],
                canvas_width: this.currentLayout.canvas_width || 1920,
                canvas_height: this.currentLayout.canvas_height || 1080,
                metadata: this.currentLayout.metadata || {}
            };

            const response = await fetch('/api/layout-opt/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`Analysis failed: ${response.statusText}`);
            }

            const result = await response.json();
            this.displayAnalysisResults(result);

        } catch (error) {
            this.showError(`Analysis failed: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    displayAnalysisResults(result) {
        this.analysisResults.style.display = 'block';
        this.optimizationSection.style.display = 'block';
        this.variantsSection.style.display = 'block';

        // Overall score
        const score = Math.round(result.score.overall_score * 100);
        this.overallScore.textContent = `${score}%`;
        this.overallScore.style.background = `conic-gradient(#48bb78 0% ${score}%, #e2e8f0 ${score}% 100%)`;

        // Score breakdown
        this.scoreBreakdown.innerHTML = '';
        Object.entries(result.score.dimensions).forEach(([dimension, value]) => {
            const dimensionScore = Math.round(value * 100);
            const div = document.createElement('div');
            div.innerHTML = `
                <strong>${dimension.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong>
                ${dimensionScore}%
            `;
            this.scoreBreakdown.appendChild(div);
        });

        // Violations
        this.violationsContainer.innerHTML = '';
        result.violations.forEach(violation => {
            const div = document.createElement('div');
            div.className = `violation-item ${violation.severity}`;
            div.innerHTML = `
                <strong>${violation.rule}:</strong> ${violation.description}
                ${violation.elements.length > 0 ? `<br><small>Elements: ${violation.elements.join(', ')}</small>` : ''}
            `;
            this.violationsContainer.appendChild(div);
        });

        // Recommendations
        this.recommendationsList.innerHTML = '';
        result.recommendations.forEach(rec => {
            const li = document.createElement('li');
            li.textContent = rec;
            this.recommendationsList.appendChild(li);
        });

        this.analysisResultsData = result;
    }

    async optimizeLayout() {
        if (!this.currentLayout) {
            this.showError('No layout loaded');
            return;
        }

        this.showLoading('Optimizing layout...');

        try {
            // Get selected overlay types
            const selectedOverlays = Array.from(document.querySelectorAll('#overlayCheckboxes input:checked'))
                .map(cb => cb.value);

            const requestData = {
                layout_data: {
                    elements: this.currentLayout.elements || [],
                    canvas_width: this.currentLayout.canvas_width || 1920,
                    canvas_height: this.currentLayout.canvas_height || 1080,
                    metadata: this.currentLayout.metadata || {}
                },
                optimization_level: this.optimizationLevel.value,
                generate_overlays: true,
                overlay_types: selectedOverlays
            };

            const response = await fetch('/api/layout-opt/optimize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`Optimization failed: ${response.statusText}`);
            }

            const result = await response.json();
            this.displayOptimizationResults(result);

        } catch (error) {
            this.showError(`Optimization failed: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    displayOptimizationResults(result) {
        this.optimizationResults.style.display = 'block';

        // Improvement score
        const improvement = Math.round(result.improvement_score * 100);
        this.improvementScore.textContent = `Improvement: ${improvement > 0 ? '+' : ''}${improvement}%`;

        // Actions applied
        this.actionsApplied.innerHTML = `<strong>Actions Applied:</strong> ${result.actions_applied.length}`;
        if (result.actions_applied.length > 0) {
            const ul = document.createElement('ul');
            result.actions_applied.slice(0, 5).forEach(action => {
                const li = document.createElement('li');
                li.textContent = action.description;
                ul.appendChild(li);
            });
            if (result.actions_applied.length > 5) {
                const li = document.createElement('li');
                li.textContent = `... and ${result.actions_applied.length - 5} more actions`;
                ul.appendChild(li);
            }
            this.actionsApplied.appendChild(ul);
        }

        // Render layout SVG
        if (result.overlays) {
            this.renderLayoutWithOverlays(result.optimized_layout, result.overlays);
        } else {
            this.renderLayoutSVG(result.optimized_layout);
        }

        this.optimizationResultsData = result;
    }

    renderLayoutSVG(layoutData) {
        // Simple SVG rendering of layout elements
        const svg = this.layoutSvg;
        const width = layoutData.canvas_width || 1920;
        const height = layoutData.canvas_height || 1080;

        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.innerHTML = '';

        // Render elements
        (layoutData.elements || []).forEach(element => {
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', element.x || 0);
            rect.setAttribute('y', element.y || 0);
            rect.setAttribute('width', element.width || 100);
            rect.setAttribute('height', element.height || 100);
            rect.setAttribute('fill', element.color || '#cccccc');
            rect.setAttribute('stroke', '#000');
            rect.setAttribute('stroke-width', '1');
            svg.appendChild(rect);

            // Add label if available
            if (element.text) {
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', (element.x || 0) + 5);
                text.setAttribute('y', (element.y || 0) + 20);
                text.setAttribute('font-size', '12');
                text.setAttribute('fill', '#000');
                text.textContent = element.text.substring(0, 20);
                svg.appendChild(text);
            }
        });
    }

    renderLayoutWithOverlays(layoutData, overlays) {
        this.renderLayoutSVG(layoutData);

        // Add overlays
        overlays.overlays.forEach(overlay => {
            const element = document.createElementNS('http://www.w3.org/2000/svg', overlay.overlay_type);

            // Set common attributes
            element.setAttribute('stroke', overlay.color);
            element.setAttribute('stroke-width', '2');
            element.setAttribute('fill', 'none');
            element.setAttribute('opacity', overlay.opacity);

            // Set type-specific attributes
            switch(overlay.overlay_type) {
                case 'alignment_guides':
                    if (overlay.width === 0) {
                        // Vertical line
                        element.setAttribute('x1', overlay.x);
                        element.setAttribute('y1', overlay.y);
                        element.setAttribute('x2', overlay.x);
                        element.setAttribute('y2', overlay.y + overlay.height);
                    } else {
                        // Horizontal line
                        element.setAttribute('x1', overlay.x);
                        element.setAttribute('y1', overlay.y);
                        element.setAttribute('x2', overlay.x + overlay.width);
                        element.setAttribute('y2', overlay.y);
                    }
                    break;
                case 'spacing_indicators':
                    element.setAttribute('x', overlay.x);
                    element.setAttribute('y', overlay.y);
                    element.setAttribute('width', overlay.width);
                    element.setAttribute('height', overlay.height);
                    element.setAttribute('fill', overlay.color);
                    element.setAttribute('fill-opacity', overlay.opacity * 0.3);
                    break;
                default:
                    // Default to rectangle
                    element.setAttribute('x', overlay.x);
                    element.setAttribute('y', overlay.y);
                    element.setAttribute('width', overlay.width);
                    element.setAttribute('height', overlay.height);
            }

            this.layoutSvg.appendChild(element);
        });

        this.updateOverlayLegend(overlays.overlay_types);
    }

    updateOverlayLegend(overlayTypes) {
        this.overlayLegend.innerHTML = '';
        overlayTypes.forEach(type => {
            const item = document.createElement('div');
            item.className = 'legend-item';
            item.innerHTML = `
                <div class="legend-color" style="background: #4ECDC4;"></div>
                <span>${type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
            `;
            this.overlayLegend.appendChild(item);
        });
    }

    toggleOverlaysVisibility() {
        const overlays = this.layoutSvg.querySelectorAll('[stroke-width="2"]');
        const isVisible = overlays[0] && overlays[0].getAttribute('opacity') !== '0';

        overlays.forEach(overlay => {
            overlay.setAttribute('opacity', isVisible ? '0' : '0.7');
        });
    }

    async generateVariants() {
        if (!this.currentLayout) {
            this.showError('No layout loaded');
            return;
        }

        this.showLoading('Generating variants...');

        try {
            // Get selected strategies
            const selectedStrategies = Array.from(document.querySelectorAll('#strategyCheckboxes input:checked'))
                .map(cb => cb.value);

            const requestData = {
                layout_data: {
                    elements: this.currentLayout.elements || [],
                    canvas_width: this.currentLayout.canvas_width || 1920,
                    canvas_height: this.currentLayout.canvas_height || 1080,
                    metadata: this.currentLayout.metadata || {}
                },
                strategies: selectedStrategies,
                count_per_strategy: parseInt(this.variantsCount.value)
            };

            const response = await fetch('/api/layout-opt/variants', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`Variant generation failed: ${response.statusText}`);
            }

            const result = await response.json();
            this.displayVariants(result);

        } catch (error) {
            this.showError(`Variant generation failed: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    displayVariants(result) {
        this.variantsResults.style.display = 'block';
        this.variantsGrid.innerHTML = '';

        result.variants.forEach((variant, index) => {
            const card = document.createElement('div');
            card.className = 'variant-card';

            card.innerHTML = `
                <h4>Variant ${index + 1}</h4>
                <div class="variant-preview">
                    <!-- SVG preview would go here -->
                    <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;">
                        Layout Preview
                    </div>
                </div>
                <div class="variant-score">Score: ${Math.round(variant.score * 100)}%</div>
                <button onclick="downloadVariant(${index})">Download</button>
            `;

            this.variantsGrid.appendChild(card);
        });

        this.variantsData = result;
    }

    showLoading(text = 'Processing...') {
        this.loadingText.textContent = text;
        this.loadingOverlay.style.display = 'flex';
    }

    hideLoading() {
        this.loadingOverlay.style.display = 'none';
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorMessage.style.display = 'block';
        setTimeout(() => {
            this.errorMessage.style.display = 'none';
        }, 5000);
    }
}

// Global function for variant download
function downloadVariant(index) {
    // Implementation would download the variant
    console.log(`Downloading variant ${index}`);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.layoutOptimizerUI = new LayoutOptimizerUI();
});