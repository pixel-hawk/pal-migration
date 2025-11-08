// Palworld Save Migration Tool - Mapping UI

// Global State
let uploadedFile = null;
let allPlayers = [];
let mappings = []; // Array of {id, source, target} objects

// DOM Elements
const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const playersSection = document.getElementById('playersSection');
const playersTableBody = document.getElementById('playersTableBody');
const playerSearch = document.getElementById('playerSearch');
const mappingsList = document.getElementById('mappingsList');
const mappingCount = document.getElementById('mappingCount');
const migrateBtn = document.getElementById('migrateBtn');
const statusMessages = document.getElementById('statusMessages');
const progressOverlay = document.getElementById('progressOverlay');
const progressText = document.getElementById('progressText');

// Initialize
function init() {
    fileInput.addEventListener('change', handleFileSelect);
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    dropZone.addEventListener('drop', handleDrop);
    playerSearch.addEventListener('input', filterPlayers);
}

init();

// File Handling
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) processFile(file);
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
    
    const maxSize = 524288000; // 500MB
    if (file.size > maxSize) {
        showToast('error', 'File too large (max 500MB)');
        return;
    }
    
    uploadedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    fileInfo.style.display = 'flex';
    
    analyzeFile();
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
}

// Analysis
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
            let errorMsg = error.detail?.message || error.detail || 'Analysis failed';
            if (error.detail?.details?.solution) {
                errorMsg += '\n\n' + error.detail.details.solution;
            }
            throw new Error(errorMsg);
        }
        
        const data = await response.json();
        allPlayers = data.players;
        populatePlayersTable();
        playersSection.style.display = 'block';
        hideProgress();
        showToast('success', `Found ${allPlayers.length} players`);
        
    } catch (error) {
        hideProgress();
        showToast('error', error.message);
    }
}

// Populate Players Table
function populatePlayersTable() {
    playersTableBody.innerHTML = '';
    
    allPlayers.forEach(player => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td title="${player.guid}">${player.guid.substring(0, 16)}...</td>
            <td>${escapeHtml(player.name)}</td>
            <td title="${player.guild_id}">${player.guild_id.substring(0, 16)}...</td>
            <td>
                <button class="btn-add-mapping" onclick='addMappingDialog(${JSON.stringify(player)})'>
                    ➕ Add Mapping
                </button>
            </td>
        `;
        playersTableBody.appendChild(row);
    });
}

// Add Mapping Dialog
function addMappingDialog(sourcePlayer) {
    // Check if already used as source
    const alreadySource = mappings.find(m => m.source.guid === sourcePlayer.guid);
    if (alreadySource) {
        showToast('warning', `${sourcePlayer.name} is already mapped to ${alreadySource.target.name}`);
        return;
    }
    
    // Create dropdown with available target players
    const usedTargets = new Set(mappings.map(m => m.target.guid));
    const availableTargets = allPlayers.filter(p => 
        p.guid !== sourcePlayer.guid && !usedTargets.has(p.guid)
    );
    
    if (availableTargets.length === 0) {
        showToast('error', 'No available target players');
        return;
    }
    
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>Create Mapping</h3>
            <p><strong>Source:</strong> ${escapeHtml(sourcePlayer.name)} (${sourcePlayer.guid.substring(0, 16)}...)</p>
            <div class="form-group">
                <label for="targetSelect">Select Target Player:</label>
                <select id="targetSelect" class="target-select">
                    <option value="">-- Select Target --</option>
                    ${availableTargets.map(p => `
                        <option value="${p.guid}">${escapeHtml(p.name)} (${p.guid.substring(0, 16)}...)</option>
                    `).join('')}
                </select>
            </div>
            <div class="modal-actions">
                <button class="btn btn-primary" onclick="confirmMapping('${sourcePlayer.guid}')">Create Mapping</button>
                <button class="btn" onclick="closeModal()">Cancel</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    setTimeout(() => modal.classList.add('show'), 10);
}

// Confirm Mapping
function confirmMapping(sourceGuid) {
    const targetGuid = document.getElementById('targetSelect').value;
    
    if (!targetGuid) {
        showToast('error', 'Please select a target player');
        return;
    }
    
    const source = allPlayers.find(p => p.guid === sourceGuid);
    const target = allPlayers.find(p => p.guid === targetGuid);
    
    mappings.push({
        id: Date.now(),
        source: source,
        target: target
    });
    
    updateMappingsList();
    closeModal();
    showToast('success', `Mapping created: ${source.name} → ${target.name}`);
}

// Update Mappings List
function updateMappingsList() {
    if (mappings.length === 0) {
        mappingsList.innerHTML = '<div class="no-mappings">No mappings created yet. Click "Add Mapping" next to a player above.</div>';
        migrateBtn.disabled = true;
        mappingCount.textContent = '0';
        return;
    }
    
    mappingsList.innerHTML = mappings.map(mapping => `
        <div class="mapping-card">
            <div class="mapping-row">
                <div class="mapping-player source">
                    <div class="player-label">Source</div>
                    <div class="player-name">${escapeHtml(mapping.source.name)}</div>
                    <div class="player-guid">${mapping.source.guid}</div>
                </div>
                <div class="mapping-arrow">→</div>
                <div class="mapping-player target">
                    <div class="player-label">Target</div>
                    <div class="player-name">${escapeHtml(mapping.target.name)}</div>
                    <div class="player-guid">${mapping.target.guid}</div>
                </div>
                <button class="btn-remove" onclick="removeMapping(${mapping.id})" title="Remove mapping">
                    ❌
                </button>
            </div>
        </div>
    `).join('');
    
    migrateBtn.disabled = false;
    mappingCount.textContent = mappings.length.toString();
}

// Remove Mapping
function removeMapping(id) {
    mappings = mappings.filter(m => m.id !== id);
    updateMappingsList();
    showToast('info', 'Mapping removed');
}

// Close Modal
function closeModal() {
    const modal = document.querySelector('.modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    }
}

// Filter Players
function filterPlayers() {
    const query = playerSearch.value.toLowerCase();
    const rows = playersTableBody.querySelectorAll('tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
    });
}

// Migration
async function performMigration() {
    if (mappings.length === 0) {
        showToast('error', 'No mappings created');
        return;
    }
    
    showProgress(`Performing ${mappings.length} migration${mappings.length > 1 ? 's' : ''}...`);
    
    const formData = new FormData();
    formData.append('file', uploadedFile);
    
    const mappingsData = mappings.map(m => ({
        source_guid: m.source.guid,
        target_guid: m.target.guid
    }));
    formData.append('mappings_json', JSON.stringify(mappingsData));
    
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
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        hideProgress();
        showToast('success', `Migration complete! ${mappings.length} player${mappings.length > 1 ? 's' : ''} migrated. Downloading...`);
        
    } catch (error) {
        hideProgress();
        showToast('error', error.message);
    }
}

// Progress Overlay
function showProgress(message) {
    progressText.textContent = message;
    progressOverlay.style.display = 'flex';
}

function hideProgress() {
    progressOverlay.style.display = 'none';
}

// Toast Notifications
function showToast(type, message) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    // Handle multi-line messages
    if (message.includes('\n')) {
        const lines = message.split('\n');
        toast.innerHTML = lines.map(line => `<p>${escapeHtml(line)}</p>`).join('');
    } else {
        toast.textContent = message;
    }
    
    statusMessages.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    
    const timeout = message.includes('\n') ? 15000 : 5000;
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, timeout);
}

// Utility
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function sortTable(tableType, column) {
    // Simple sort - refresh table with sorted data
    allPlayers.sort((a, b) => {
        const aVal = a[column] || '';
        const bVal = b[column] || '';
        return aVal.localeCompare(bVal);
    });
    populatePlayersTable();
}
