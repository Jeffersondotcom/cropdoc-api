// Initialize Lucide Icons
lucide.createIcons();

// ===== DOM ELEMENTS =====
// Navigation
const navItems = document.querySelectorAll('.nav-item');
const viewSections = document.querySelectorAll('.view-section');

// Scan View Elements
const btnOpenCamera = document.getElementById('btn-open-camera');
const btnOpenGallery = document.getElementById('btn-open-gallery');
const cameraInput = document.getElementById('camera-input');
const galleryInput = document.getElementById('gallery-input');

// Scan States
const scanPrompt = document.getElementById('scan-prompt');
const scanPreview = document.getElementById('scan-preview');
const scanResult = document.getElementById('scan-result');

// Preview Elements
const previewImage = document.getElementById('preview-image');
const btnRetake = document.getElementById('btn-retake');
const btnConfirmScan = document.getElementById('btn-confirm-scan');

// Result Elements
const resultDisease = document.getElementById('result-disease');
const resultSeverity = document.getElementById('result-severity');
const confidenceCircle = document.getElementById('confidence-circle');
const confidenceValue = document.getElementById('confidence-value');
const resultTreatment = document.getElementById('result-treatment');
const btnNewScan = document.getElementById('btn-new-scan');

// Loading Overlay
const loadingOverlay = document.getElementById('loading-overlay');

// State
let selectedFile = null;

// ===== NAVIGATION =====
navItems.forEach(item => {
    item.addEventListener('click', () => {
        // Update active nav
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');

        // Update active view
        const targetId = item.getAttribute('data-target');
        viewSections.forEach(section => {
            if (section.id === targetId) {
                section.classList.add('active');
            } else {
                section.classList.remove('active');
            }
        });
    });
});

// ===== FILE SELECTION =====
btnOpenCamera.addEventListener('click', () => cameraInput.click());
btnOpenGallery.addEventListener('click', () => galleryInput.click());

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    selectedFile = file;
    
    // Create preview URL
    const previewUrl = URL.createObjectURL(file);
    previewImage.src = previewUrl;

    // Switch views
    scanPrompt.classList.add('hidden');
    scanPreview.classList.remove('hidden');
    scanResult.classList.add('hidden');

    // Reset input
    event.target.value = '';
}

cameraInput.addEventListener('change', handleFileSelect);
galleryInput.addEventListener('change', handleFileSelect);

// ===== PREVIEW ACTIONS =====
btnRetake.addEventListener('click', () => {
    selectedFile = null;
    previewImage.src = '';
    
    scanPreview.classList.add('hidden');
    scanPrompt.classList.remove('hidden');
});

btnConfirmScan.addEventListener('click', async () => {
    if (!selectedFile) return;

    loadingOverlay.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        const response = await fetch('/predict', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Prediction failed');

        const data = await response.json();
        displayResults(data);
    } catch (error) {
        alert('Sorry, there was an error analyzing the crop. Please try again.');
        console.error(error);
        loadingOverlay.classList.add('hidden');
    }
});

// ===== RESULTS =====
function displayResults(data) {
    loadingOverlay.classList.add('hidden');
    scanPreview.classList.add('hidden');
    scanResult.classList.remove('hidden');

    // Populate data
    resultDisease.textContent = data.disease;
    resultSeverity.textContent = data.severity;
    resultSeverity.className = `severity-badge ${data.severity}`;
    
    const isHealthy = data.disease.includes('Healthy');
    if (isHealthy) {
        resultTreatment.textContent = "Your crop appears to be healthy. Continue with standard care.";
    } else {
        resultTreatment.textContent = data.treatment || "Please consult a local agricultural expert for treatment.";
    }

    // Animate confidence circle
    const conf = data.confidence;
    confidenceValue.textContent = `${conf}%`;
    
    // Use setTimeout to ensure CSS transition triggers
    setTimeout(() => {
        confidenceCircle.style.background = `conic-gradient(var(--accent) ${conf}%, var(--bg-tertiary) ${conf}%)`;
    }, 50);

    // Re-initialize Lucide icons for new elements if needed
    lucide.createIcons();
}

btnNewScan.addEventListener('click', () => {
    selectedFile = null;
    previewImage.src = '';
    
    // Reset confidence circle
    confidenceCircle.style.background = `conic-gradient(var(--accent) 0%, var(--bg-tertiary) 0%)`;
    
    scanResult.classList.add('hidden');
    scanPrompt.classList.remove('hidden');
});
