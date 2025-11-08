// Palworld Save Migration Tool - JavaScript

// Global State
let uploadedFile = null;
let allPlayers = [];
let sourceSelectedGuid = null;
let targetSelectedGuid = null;

// DOM Elements
const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const playersSection = document.getElementById('playersSection');
const sourceTableBody = document.getElementById('sourceTableBody');
const targetTableBody = document.getElementById('targetTableBody');
const sourceSearch = document.getElementById('sourceSearch');
const targetSearch = document.getElementById('targetSearch');
const sourceSelection = document.getElementById('sourceSelection');
const targetSelection = document.getElementById('targetSelection');
const migrateBtn = document.getElementById('migrateBtn');
const statusMessages = document.getElementById('statusMessages');
const progressOverlay = document.getElementById('progressOverlay');
const progressText = document.getElementById('progressText');

// Initialize Event Listeners
function init() {
    // File input change
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', handleDragOver);
    dropZone.addEventListener('dragleave', handleDragLeave);
    dropZone.addEventListener('drop', handleDrop);
    
    // Search inputs
    sourceSearch.addEventListener('input', () => filterTable('source'));
    targetSearch.addEventListener('input', () => filterTable('target'));
}

// File Handling
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        processFile(file);
    }
}

function handleDragOver(event) {
    event.preventDefault();
    dropZone.classList.add('dragover');
}

function handleDragLeave() {
    dropZone.classList.remove('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    dropZone.classList.remove('dragover');
    
    const file = event.dataTransfer.files[0];
    if (file) {
        fileInput.files = event.dataTransfer.files;
        processFile(file);
    }
}

function processFile(file) {
    if (!file.name.endsWith('.zip')) {
        showToast('error', 'Please select a .zip file');
        return;
    }
    
    if (file.size > 524288000) { // 500MB
        showToast('error', 'File too large (max 500MB)');
        return;
    }
    
    uploadedFile = file;
    
    // Show file info
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileInfo.style.display = 'flex';
    
    // Analyze the file
    analyzeFile();
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
}

// Analyze Endpoint
async function analyzeFile() {
    showProgress('Analyzing save file...');
    
    const formData = new FormData();
    formData.append('file', uploadedFile);
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            let errorMessage = error.detail?.message || error.detail || 'Analysis failed';
            
            // Add solution if available
            if (error.detail?.details?.solution) {
                errorMessage += '\n\n' + error.detail.details.solution;
            }
            
            throw new Error(errorMessage);
        }
        
        const data = await response.json();
        allPlayers = data.players;
        
        hideProgress();
        showToast('success', `Found ${allPlayers.length} players in save file`);
        
        // Populate tables
        populateTables();
        playersSection.style.display = 'block';
        
    } catch (error) {
        hideProgress();
        showToast('error', `Analysis failed: ${error.message}`);
        console.error('Analysis error:', error);
    }
}

// Table Population
function populateTables() {
    populateTable('source', allPlayers);
    populateTable('target', allPlayers);
}

function populateTable(tableType, players) {
    const tbody = tableType === 'source' ? sourceTableBody : targetTableBody;
    tbody.innerHTML = '';
    
    players.forEach(player => {
        const row = document.createElement('tr');
        row.dataset.guid = player.guid;
        row.dataset.name = player.name;
        row.dataset.guild = player.guild_id;
        
        row.innerHTML = `
            <td title="${player.guid}">${player.guid.substring(0, 16)}...</td>
            <td title="${player.name}">${player.name}</td>
            <td title="${player.guild_id}">${player.guild_id.substring(0, 16)}...</td>
        `;
        
        row.addEventListener('click', () => selectPlayer(tableType, player));
        tbody.appendChild(row);
    });
}

// Player Selection
function selectPlayer(tableType, player) {
    if (tableType === 'source') {
        sourceSelectedGuid = player.guid;
        
        // Update UI
        sourceTableBody.querySelectorAll('tr').forEach(tr => {
            tr.classList.toggle('selected', tr.dataset.guid === player.guid);
        });
        
        sourceSelection.textContent = `Selected: ${player.name} (${player.guid})`;
        sourceSelection.classList.add('selected');
    } else {
        targetSelectedGuid = player.guid;
        
        // Update UI
        targetTableBody.querySelectorAll('tr').forEach(tr => {
            tr.classList.toggle('selected', tr.dataset.guid === player.guid);
        });
        
        targetSelection.textContent = `Selected: ${player.name} (${player.guid})`;
        targetSelection.classList.add('selected');
    }
    
    // Enable migrate button if both selected and different
    updateMigrateButton();
}

function updateMigrateButton() {
    const bothSelected = sourceSelectedGuid && targetSelectedGuid;
    const different = sourceSelectedGuid !== targetSelectedGuid;
    
    migrateBtn.disabled = !(bothSelected && different);
    
    if (bothSelected && !different) {
        showToast('warning', 'Please select two different players');
    }
}

// Search/Filter
function filterTable(tableType) {
    const searchInput = tableType === 'source' ? sourceSearch : targetSearch;
    const tbody = tableType === 'source' ? sourceTableBody : targetTableBody;
    const query = searchInput.value.toLowerCase();
    
    tbody.querySelectorAll('tr').forEach(row => {
        const guid = row.dataset.guid.toLowerCase();
        const name = row.dataset.name.toLowerCase();
        const guild = row.dataset.guild.toLowerCase();
        
        const matches = guid.includes(query) || name.includes(query) || guild.includes(query);
        row.style.display = matches ? '' : 'none';
    });
}

// Sort Table
function sortTable(tableType, column) {
    const tbody = tableType === 'source' ? sourceTableBody : targetTableBody;
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        let aVal = a.dataset[column] || '';
        let bVal = b.dataset[column] || '';
        return aVal.localeCompare(bVal);
    });
    
    tbody.innerHTML = '';
    rows.forEach(row => tbody.appendChild(row));
}

// Migration
async function performMigration() {
    if (!sourceSelectedGuid || !targetSelectedGuid) {
        showToast('error', 'Please select both source and target players');
        return;
    }
    
    if (sourceSelectedGuid === targetSelectedGuid) {
        showToast('error', 'Source and target must be different');
        return;
    }
    
    showProgress('Performing GUID migration... This may take a few seconds.');
    
    const formData = new FormData();
    formData.append('file', uploadedFile);
    formData.append('source_guid', sourceSelectedGuid);
    formData.append('target_guid', targetSelectedGuid);
    
    try {
        const response = await fetch('/migrate', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail?.message || error.detail || 'Migration failed');
        }
        
        // Download the migrated zip
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'migrated.zip';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        
        hideProgress();
        showToast('success', 'Migration complete! Download started. Extract the zip and replace your save folder.');
        
    } catch (error) {
        hideProgress();
        showToast('error', `Migration failed: ${error.message}`);
        console.error('Migration error:', error);
    }
}

// UI Helpers
function showProgress(message) {
    progressText.textContent = message;
    progressOverlay.style.display = 'flex';
}

function hideProgress() {
    progressOverlay.style.display = 'none';
}

function showToast(type, message) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    // Handle multiline messages
    if (message.includes('\n')) {
        const lines = message.split('\n');
        lines.forEach((line, index) => {
            if (line.trim()) {
                const p = document.createElement('p');
                p.textContent = line;
                if (index > 0) p.style.marginTop = '10px';
                toast.appendChild(p);
            }
        });
    } else {
        toast.textContent = message;
    }
    
    statusMessages.appendChild(toast);
    
    // Auto-remove after 10 seconds (longer for multi-line errors)
    const duration = message.includes('\n') ? 15000 : 5000;
    setTimeout(() => {
        toast.remove();
    }, duration);
}

// Initialize on load
document.addEventListener('DOMContentLoaded', init);
