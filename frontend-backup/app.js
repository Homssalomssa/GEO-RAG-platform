/**
 * Geo-RAG Frontend — Image Upload & Analysis
 * Handles multiple image uploads, mode selection, and result polling
 */

const API_BASE = window.location.origin;
let selectedFiles = [];
let selectedMode = 'rag_baseline';

// DOM Elements
const uploadZone = document.getElementById('uploadZone');
const imageInput = document.getElementById('imageInput');
const imageGrid = document.getElementById('imageGrid');
const questionInput = document.getElementById('questionInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const uploadSection = document.getElementById('uploadSection');
const resultsSection = document.getElementById('resultsSection');
const backBtn = document.getElementById('backBtn');
const loadingContainer = document.getElementById('loadingContainer');
const loadingText = document.getElementById('loadingText');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const charCount = document.getElementById('charCount');
const systemStatus = document.getElementById('systemStatus');
const navItems = document.querySelectorAll('.nav-item');

// --- Upload Handling ---

uploadZone.addEventListener('click', () => imageInput.click());

imageInput.addEventListener('change', (e) => {
    for (let file of e.target.files) {
        handleImageSelect(file);
    }
});

uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    for (let file of e.dataTransfer.files) {
        handleImageSelect(file);
    }
});

function handleImageSelect(file) {
    const validTypes = ['image/jpeg', 'image/png', 'image/tiff', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        alert('Unsupported image type. Please use JPEG, PNG, TIFF, or WebP.');
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        alert('Image too large. Maximum size is 10MB.');
        return;
    }

    selectedFiles.push(file);
    displayImagePreviews();
    updateAnalyzeButton();
}

function displayImagePreviews() {
    if (selectedFiles.length === 0) {
        imageGrid.style.display = 'none';
        return;
    }

    imageGrid.style.display = 'grid';
    imageGrid.innerHTML = '';

    selectedFiles.forEach((file, index) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const item = document.createElement('div');
            item.className = 'image-preview-item';
            item.innerHTML = `
                <img src="${e.target.result}" alt="Image ${index + 1}">
                <button class="remove-btn" onclick="removeImage(${index})">×</button>
            `;
            imageGrid.appendChild(item);
        };
        reader.readAsDataURL(file);
    });
}

function removeImage(index) {
    selectedFiles.splice(index, 1);
    displayImagePreviews();
    updateAnalyzeButton();
}

// --- Form Input ---

questionInput.addEventListener('input', () => {
    charCount.textContent = questionInput.value.length;
    updateAnalyzeButton();
});

document.querySelectorAll('input[name="analysisMode"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        selectedMode = e.target.value;
    });
});

function updateAnalyzeButton() {
    analyzeBtn.disabled = selectedFiles.length === 0 || !questionInput.value.trim();
}

// --- Analysis ---

analyzeBtn.addEventListener('click', async () => {
    if (selectedFiles.length === 0 || !questionInput.value.trim()) return;

    uploadSection.classList.remove('active');
    resultsSection.classList.add('active');
    loadingContainer.style.display = 'block';

    try {
        const results = [];
        for (let i = 0; i < selectedFiles.length; i++) {
            updateLoadingText(`Analyzing image ${i + 1} of ${selectedFiles.length}...`);
            const result = await analyzeImage(selectedFiles[i]);
            results.push(result);
        }

        displayResults(results);
    } catch (err) {
        loadingContainer.style.display = 'none';
        document.getElementById('resultsContainer').innerHTML = `
            <div style="padding: 24px; text-align: center; color: var(--danger);">
                <p>Error: ${err.message}</p>
            </div>
        `;
    }
});

async function analyzeImage(imageFile) {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('question', questionInput.value.trim());
    formData.append('mode', selectedMode);

    // Submit job
    const submitResponse = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        body: formData,
    });

    if (!submitResponse.ok) {
        throw new Error(`Submit failed: ${submitResponse.status}`);
    }

    const submitData = await submitResponse.json();
    const jobId = submitData.job_id;

    // Poll for results
    let pollCount = 0;
    const maxPolls = 300;

    while (pollCount < maxPolls) {
        const statusResponse = await fetch(`${API_BASE}/api/status/${jobId}`);

        if (!statusResponse.ok) {
            throw new Error(`Status check failed: ${statusResponse.status}`);
        }

        const statusData = await statusResponse.json();
        const progress = statusData.progress || 0;
        progressFill.style.width = progress + '%';
        progressText.textContent = progress + '%';

        if (statusData.status === 'completed') {
            return {
                fileName: imageFile.name,
                mode: selectedMode,
                answer: statusData.result || '',
                visionFeatures: statusData.vision_features || {},
                retrievedContext: statusData.retrieved_context || [],
                gisData: statusData.gis_data,
                timing: statusData.processing_seconds ? Math.round(statusData.processing_seconds * 1000) : 0
            };
        }

        if (statusData.status === 'failed') {
            throw new Error(`Analysis failed: ${statusData.error}`);
        }

        await new Promise(resolve => setTimeout(resolve, 500));
        pollCount++;
    }

    throw new Error('Analysis timeout');
}

function displayResults(results) {
    loadingContainer.style.display = 'none';

    const resultsContainer = document.getElementById('resultsContainer');
    resultsContainer.innerHTML = '';

    const resultGrid = document.createElement('div');
    resultGrid.className = 'result-grid';

    results.forEach((result) => {
        const card = document.createElement('div');
        card.className = 'result-card';
        card.innerHTML = `
            <h4>
                <span>${result.fileName}</span>
                <span style="margin-left: auto; font-size: 12px; color: var(--text-light);">${result.timing}ms</span>
            </h4>

            <div class="result-section">
                <div class="result-section-title">Analysis Result</div>
                <div class="answer-text">${escapeHtml(result.answer)}</div>
            </div>

            ${result.visionFeatures && Object.keys(result.visionFeatures).length > 0 ? `
            <div class="result-section">
                <div class="result-section-title">Vision Features</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;">
                    ${Object.entries(result.visionFeatures).map(([key, val]) => `
                        <div style="padding: 8px; background: var(--primary-light); border-radius: 4px;">
                            <strong>${key.replace(/_/g, ' ')}</strong><br>
                            <span style="color: var(--text-secondary);">${val}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}

            ${result.retrievedContext && result.retrievedContext.length > 0 ? `
            <div class="result-section">
                <div class="result-section-title">Retrieved Knowledge (${result.retrievedContext.length})</div>
                <div style="max-height: 200px; overflow-y: auto;">
                    ${result.retrievedContext.map((chunk, idx) => `
                        <div style="padding: 8px; margin-bottom: 8px; background: var(--bg-main); border-radius: 4px; font-size: 12px; border-left: 3px solid var(--primary);">
                            <p style="margin-bottom: 4px;">${escapeHtml(typeof chunk === 'string' ? chunk : chunk.chunk).substring(0, 150)}...</p>
                            <span style="color: var(--text-light);">Score: ${typeof chunk === 'object' ? chunk.score.toFixed(2) : 'N/A'}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}

            ${result.gisData ? `
            <div class="result-section">
                <div class="result-section-title">GIS Data</div>
                <div style="padding: 8px; background: var(--primary-light); border-radius: 4px; font-size: 12px;">
                    ${Object.entries(result.gisData).map(([key, val]) => `
                        <div><strong>${key}:</strong> ${val}</div>
                    `).join('')}
                </div>
            </div>
            ` : ''}
        `;
        resultGrid.appendChild(card);
    });

    resultsContainer.appendChild(resultGrid);
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function updateLoadingText(text) {
    loadingText.textContent = text;
}

// --- Navigation ---

backBtn.addEventListener('click', () => {
    resultsSection.classList.remove('active');
    uploadSection.classList.add('active');
});

navItems.forEach(item => {
    item.addEventListener('click', () => {
        const section = item.dataset.section;
        navItems.forEach(i => i.classList.remove('active'));
        item.classList.add('active');

        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        if (section === 'upload') {
            uploadSection.classList.add('active');
        } else if (section === 'results') {
            resultsSection.classList.add('active');
        }
    });
});

// --- System Health ---

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        if (response.ok) {
            systemStatus.innerHTML = '<span class="dot online"></span><span>System online</span>';
        } else {
            systemStatus.innerHTML = '<span class="dot"></span><span>System unavailable</span>';
        }
    } catch {
        systemStatus.innerHTML = '<span class="dot"></span><span>Offline</span>';
    }
}

checkHealth();
setInterval(checkHealth, 30000);

// Initialize
uploadSection.classList.add('active');
updateAnalyzeButton();
