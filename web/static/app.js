document.addEventListener('DOMContentLoaded', () => {
    // --- Element Selectors ---
    const vendorSelect = document.getElementById('vendor-select');
    const avpContainer = document.getElementById('avp-container');
    const sequenceList = document.getElementById('sequence-list');
    const executeBtn = document.getElementById('execute-btn');
    const clearSequenceBtn = document.getElementById('clear-sequence-btn');
    const clearLogBtn = document.getElementById('clear-log-btn');
    const copyLogBtn = document.getElementById('copy-log-btn');
    const exportLogBtn = document.getElementById('export-log-btn');
    const closeLogBtn = document.getElementById('close-log-btn');
    const outputLog = document.getElementById('output-log');
    const themeToggle = document.getElementById('theme-toggle');
    const logToggle = document.getElementById('log-toggle');
    const packetModal = document.getElementById('packet-modal');
    const packetPreview = document.getElementById('packet-preview');
    const presetSelect = document.getElementById('preset-select');
    const savePresetBtn = document.getElementById('save-preset-btn');
    const radiusServerInput = document.getElementById('radius-server');
    const radiusSecretInput = document.getElementById('radius-secret');
    const testConnectionBtn = document.getElementById('test-connection-btn');
    const packetHistory = document.getElementById('packet-history');
    const clearHistoryBtn = document.getElementById('clear-history-btn');
    const exportConfigBtn = document.getElementById('export-config-btn');
    const importConfigBtn = document.getElementById('import-config-btn');

    // --- State Management ---
    let isExecuting = false;
    let stopExecution = false;
    let currentPreset = null;
    let historyItems = [];

    // --- THEME MANAGEMENT ---
    const applyTheme = (theme) => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        const icon = themeToggle.querySelector('i');
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    };

    themeToggle.addEventListener('click', (e) => {
        e.preventDefault();
        const newTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
    });

    // Initialize theme
    const savedTheme = localStorage.getItem('theme') || 
        (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    applyTheme(savedTheme);

    // --- LOG DRAWER MANAGEMENT ---
    const toggleLog = () => {
        document.body.classList.toggle('log-open');
        const isOpen = document.body.classList.contains('log-open');
        localStorage.setItem('logOpen', isOpen);
        logToggle.classList.toggle('active', isOpen);
    };

    logToggle.addEventListener('click', (e) => {
        e.preventDefault();
        toggleLog();
    });

    closeLogBtn.addEventListener('click', () => {
        toggleLog();
    });

    // Initialize log state
    const savedLogState = localStorage.getItem('logOpen') === 'true';
    if (savedLogState) {
        document.body.classList.add('log-open');
        logToggle.classList.add('active');
    }

    // --- TOAST NOTIFICATIONS ---
    const showToast = (message, type = 'success') => {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease-out reverse';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    };

    // --- CONNECTION TEST ---
    testConnectionBtn?.addEventListener('click', async () => {
        const originalHTML = testConnectionBtn.innerHTML;
        testConnectionBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
        testConnectionBtn.disabled = true;
        
        try {
            const response = await fetch('/api/test_connection', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    server: radiusServerInput.value,
                    secret: radiusSecretInput.value,
                    vendor: vendorSelect.value
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                showToast(result.message, 'success');
            } else {
                showToast(result.message, 'error');
            }
        } catch (error) {
            showToast(`Connection test failed: ${error.message}`, 'error');
        } finally {
            testConnectionBtn.innerHTML = originalHTML;
            testConnectionBtn.disabled = false;
        }
    });

    // --- AVP MANAGEMENT ---
    const fetchAvps = async (vendor) => {
        avpContainer.innerHTML = '<progress></progress>';
        try {
            const response = await fetch(`/api/get_defaults/${vendor}`);
            if (!response.ok) throw new Error(`Server returned ${response.status}`);
            const avps = await response.json();
            
            avpContainer.innerHTML = '';
            for (const [key, value] of Object.entries(avps)) {
                const field = document.createElement('div');
                field.className = 'avp-field';
                field.innerHTML = `
                    <label>${key.replace(/_/g, '-')}</label>
                    <input type="text" name="${key}" value="${value}">
                `;
                avpContainer.appendChild(field);
            }
        } catch (error) {
            avpContainer.innerHTML = `<p style="color: var(--danger);">Error: ${error.message}</p>`;
            showToast('Failed to load AVPs', 'error');
        }
    };

    // --- SEQUENCE MANAGEMENT ---
    const commandIcons = {
        'auth': 'fa-key',
        'start': 'fa-play',
        'alive': 'fa-heartbeat',
        'stop': 'fa-stop'
    };

    const checkPresetMatch = () => {
        const currentSequence = Array.from(sequenceList.querySelectorAll('li')).map(li => li.dataset.command);
        let matched = false;

        for (const [presetName, preset] of Object.entries(presets)) {
            if (JSON.stringify(preset.sequence) === JSON.stringify(currentSequence)) {
                currentPreset = presetName;
                presetSelect.value = presetName;
                matched = true;
                break;
            }
        }
        
        if (!matched) {
            currentPreset = null;
            presetSelect.value = '';
        }
    };

    const addSequenceStep = (command, skipPresetCheck = false) => {
        const li = document.createElement('li');
        li.dataset.command = command;
        li.draggable = true;
        
        li.innerHTML = `
            <div class="step-info">
                <div class="step-icon">
                    <i class="fas ${commandIcons[command]}"></i>
                </div>
                <span class="step-name">${command.charAt(0).toUpperCase() + command.slice(1)}</span>
            </div>
            <div class="step-actions">
                <button class="step-btn preview-btn" title="Preview packet">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="step-btn remove-btn" title="Remove">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        li.querySelector('.step-name').onclick = () => showPacketPreview(command);
        li.querySelector('.preview-btn').onclick = () => showPacketPreview(command);
        li.querySelector('.remove-btn').onclick = () => {
            li.style.animation = 'slideIn 0.3s ease-out reverse';
            setTimeout(() => {
                li.remove();
                checkPresetMatch();
            }, 300);
        };
        
        li.addEventListener('dragstart', handleDragStart);
        li.addEventListener('dragover', handleDragOver);
        li.addEventListener('drop', handleDrop);
        li.addEventListener('dragend', handleDragEnd);
        
        sequenceList.appendChild(li);
        
        if (!skipPresetCheck) {
            showToast(`Added ${command} to sequence`, 'success');
            checkPresetMatch();
        }
    };

    // Drag and Drop handlers
    let draggedElement = null;

    const handleDragStart = (e) => {
        draggedElement = e.target;
        e.target.style.opacity = '0.5';
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        return false;
    };

    const handleDrop = (e) => {
        e.preventDefault();
        if (draggedElement !== e.currentTarget) {
            const allItems = Array.from(sequenceList.children);
            const draggedIndex = allItems.indexOf(draggedElement);
            const targetIndex = allItems.indexOf(e.currentTarget);
            
            if (draggedIndex < targetIndex) {
                e.currentTarget.after(draggedElement);
            } else {
                e.currentTarget.before(draggedElement);
            }
            
            checkPresetMatch();
        }
        return false;
    };

    const handleDragEnd = (e) => {
        e.target.style.opacity = '';
        draggedElement = null;
    };

    document.querySelectorAll('.sequence-actions button').forEach(btn => {
        btn.addEventListener('click', () => {
            const command = btn.dataset.command;
            addSequenceStep(command);
        });
    });

    clearSequenceBtn.addEventListener('click', () => {
        sequenceList.innerHTML = '';
        currentPreset = null;
        presetSelect.value = '';
        showToast('Sequence cleared', 'success');
    });

    // --- PACKET HISTORY ---
    const addToHistory = (command, success, timestamp, responseTime) => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem; border-bottom: 1px solid var(--border);">
                <div class="step-icon" style="width: 24px; height: 24px;">
                    <i class="fas ${commandIcons[command]}"></i>
                </div>
                <span style="flex: 1; font-size: 0.75rem; font-weight: 600;">
                    ${command.toUpperCase()}
                </span>
                <span style="font-size: 0.7rem; color: var(--text-muted);">
                    ${responseTime ? responseTime.toFixed(0) + 'ms' : 'N/A'}
                </span>
                <span style="font-size: 0.7rem; color: var(--text-muted);">
                    ${new Date(timestamp).toLocaleTimeString()}
                </span>
                <span class="status-badge ${success ? 'status-accept' : 'status-reject'}">
                    ${success ? 'OK' : 'FAIL'}
                </span>
            </div>
        `;
        
        if (packetHistory.querySelector('p')) {
            packetHistory.innerHTML = '';
        }
        
        packetHistory.insertBefore(historyItem, packetHistory.firstChild);
        historyItems.push({ command, success, timestamp, responseTime });
        
        if (historyItems.length > 20) {
            packetHistory.removeChild(packetHistory.lastChild);
            historyItems.shift();
        }
    };

    clearHistoryBtn?.addEventListener('click', () => {
        packetHistory.innerHTML = `
            <p style="text-align: center; color: var(--text-muted); font-size: 0.8rem; padding: 2rem;">
                No packets yet. Execute a sequence to see history.
            </p>
        `;
        historyItems = [];
        showToast('History cleared', 'success');
    });

    // --- MODAL & PREVIEW ---
    const showPacketPreview = async (command) => {
        packetModal.showModal();
        packetPreview.textContent = 'Generating packet preview...';
        
        const payload = {
            username: document.getElementById('username').value,
            password: document.getElementById('password').value,
            vendor: vendorSelect.value,
            command: command,
            server: radiusServerInput.value,
            secret: radiusSecretInput.value,
            avps: {}
        };
        
        avpContainer.querySelectorAll('input').forEach(input => {
            payload.avps[input.name] = input.value;
        });

        try {
            const response = await fetch('/api/preview_packet', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            packetPreview.textContent = result.error || result.packet_details;
        } catch (error) {
            packetPreview.textContent = `Error: ${error.message}`;
            showToast('Failed to generate preview', 'error');
        }
    };

    packetModal.addEventListener('click', (e) => {
        if (e.target === packetModal || e.target.closest('.close')) {
            packetModal.close();
        }
    });

    // --- EXECUTION ---
    const executeStep = async (payload) => {
        try {
            const response = await fetch('/api/execute_step', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            return await response.json();
        } catch (error) {
            return { success: false, log: `Network error: ${error.message}` };
        }
    };

    const runSequence = async () => {
        if (isExecuting) {
            stopExecution = true;
            appendToLog('\n⏹️ EXECUTION HALTED BY USER\n');
            showToast('Execution stopped', 'warning');
            return;
        }

        const sequenceItems = sequenceList.querySelectorAll('li');
        if (sequenceItems.length === 0) {
            showToast('No sequence to execute', 'warning');
            return;
        }

        if (!radiusServerInput.value.trim()) {
            showToast('Please enter a RADIUS server', 'error');
            radiusServerInput.focus();
            return;
        }
        
        if (!radiusSecretInput.value.trim()) {
            showToast('Please enter a RADIUS secret', 'error');
            radiusSecretInput.focus();
            return;
        }

        if (!document.body.classList.contains('log-open')) {
            toggleLog();
        }

        isExecuting = true;
        stopExecution = false;
        
        const timestamp = new Date().toISOString();
        outputLog.textContent = `🚀 EXECUTION STARTED AT ${timestamp}\n`;
        outputLog.textContent += `📡 Server: ${radiusServerInput.value}\n`;
        outputLog.textContent += `🔑 Vendor: ${vendorSelect.value}\n`;
        outputLog.textContent += `👤 Username: ${document.getElementById('username').value}\n`;
        outputLog.textContent += '='.repeat(60) + '\n\n';
        
        executeBtn.innerHTML = '<i class="fas fa-stop-circle"></i> Stop';
        executeBtn.className = 'btn-danger';

        const basePayload = {
            username: document.getElementById('username').value,
            password: document.getElementById('password').value,
            vendor: vendorSelect.value,
            server: radiusServerInput.value,
            secret: radiusSecretInput.value,
            avps: {}
        };
        
        avpContainer.querySelectorAll('input').forEach(input => {
            basePayload.avps[input.name] = input.value;
        });
        
        let successCount = 0;
        let errorCount = 0;
        let totalTime = 0;

        for (let i = 0; i < sequenceItems.length; i++) {
            if (stopExecution) break;
            
            const item = sequenceItems[i];
            const command = item.dataset.command;
            
            appendToLog(`\n[${i + 1}/${sequenceItems.length}] 📤 ${command.toUpperCase()}\n`);
            appendToLog('-'.repeat(60) + '\n');
            
            const stepStart = performance.now();
            const result = await executeStep({ ...basePayload, command });
            const stepTime = performance.now() - stepStart;
            totalTime += stepTime;
            
            appendToLog(result.log);
            
            if (result.success) {
                successCount++;
                addToHistory(command, true, Date.now(), stepTime);
                appendToLog(`\n✅ Step ${i + 1} completed in ${stepTime.toFixed(0)}ms\n`);
            } else {
                errorCount++;
                addToHistory(command, false, Date.now(), stepTime);
                appendToLog(`\n❌ Step ${i + 1} FAILED after ${stepTime.toFixed(0)}ms\n`);
                
                if (i < sequenceItems.length - 1) {
                    appendToLog('\n⚠️  Error encountered. Stopping execution.\n');
                    break;
                }
            }
            
            if (i < sequenceItems.length - 1 && !stopExecution) {
                appendToLog('\n⏳ Waiting 500ms before next step...\n');
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        }

        if (!stopExecution) {
            appendToLog('\n' + '='.repeat(60));
            appendToLog(`\n\n📊 EXECUTION SUMMARY`);
            appendToLog(`\n   Total Steps: ${sequenceItems.length}`);
            appendToLog(`\n   ✅ Successful: ${successCount}`);
            appendToLog(`\n   ❌ Failed: ${errorCount}`);
            appendToLog(`\n   ⏱️  Total Time: ${totalTime.toFixed(0)}ms`);
            appendToLog(`\n   ⌀ Avg Time/Step: ${(totalTime / sequenceItems.length).toFixed(0)}ms\n`);
            
            showToast(
                `Complete: ${successCount}/${sequenceItems.length} successful`, 
                errorCount > 0 ? 'warning' : 'success'
            );
        }

        isExecuting = false;
        executeBtn.innerHTML = '<i class="fas fa-play-circle"></i> Execute Sequence';
        executeBtn.className = 'btn-primary';
    };

    executeBtn.addEventListener('click', runSequence);

    // --- LOG CONTROLS ---
    const appendToLog = (message) => {
        outputLog.textContent += message + '\n';
        outputLog.scrollTop = outputLog.scrollHeight;
    };

    clearLogBtn.addEventListener('click', () => {
        outputLog.textContent = '';
        showToast('Log cleared', 'success');
    });

    copyLogBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(outputLog.textContent).then(() => {
            showToast('Log copied to clipboard', 'success');
        }).catch(() => {
            showToast('Failed to copy log', 'error');
        });
    });

    exportLogBtn.addEventListener('click', () => {
        const blob = new Blob([outputLog.textContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `radius-log-${new Date().toISOString()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('Log exported', 'success');
    });

    // --- CONFIG IMPORT/EXPORT ---
    const exportConfig = () => {
        const config = {
            server: radiusServerInput.value,
            secret: radiusSecretInput.value,
            vendor: vendorSelect.value,
            username: document.getElementById('username').value,
            sequence: Array.from(sequenceList.querySelectorAll('li')).map(li => li.dataset.command),
            avps: {}
        };
        
        avpContainer.querySelectorAll('input').forEach(input => {
            config.avps[input.name] = input.value;
        });
        
        const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `radius-config-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('Configuration exported', 'success');
    };

    const importConfig = (file) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const config = JSON.parse(e.target.result);
                radiusServerInput.value = config.server || '127.0.0.1';
                radiusSecretInput.value = config.secret || 'secret';
                vendorSelect.value = config.vendor || 'mikrotik';
                document.getElementById('username').value = config.username || '';
                
                sequenceList.innerHTML = '';
                config.sequence?.forEach(cmd => addSequenceStep(cmd, true));
                
                fetchAvps(vendorSelect.value).then(() => {
                    Object.entries(config.avps || {}).forEach(([key, value]) => {
                        const input = avpContainer.querySelector(`input[name="${key}"]`);
                        if (input) input.value = value;
                    });
                });
                
                showToast('Configuration imported', 'success');
            } catch (error) {
                showToast('Failed to import configuration', 'error');
            }
        };
        reader.readAsText(file);
    };

    exportConfigBtn?.addEventListener('click', exportConfig);

    importConfigBtn?.addEventListener('click', () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) importConfig(file);
        };
        input.click();
    });

    // --- PRESET MANAGEMENT ---
    const presets = {
        'basic-auth': {
            sequence: ['auth']
        },
        'full-session': {
            sequence: ['auth', 'start', 'alive', 'stop']
        },
        'accounting-only': {
            sequence: ['start', 'alive', 'stop']
        }
    };

    presetSelect.addEventListener('change', (e) => {
        const presetName = e.target.value;
        if (!presetName) return;
        
        const preset = presets[presetName];
        if (preset) {
            sequenceList.innerHTML = '';
            currentPreset = presetName;
            preset.sequence.forEach(cmd => addSequenceStep(cmd, true));
            showToast(`Preset "${presetName}" loaded`, 'success');
        }
    });

    savePresetBtn.addEventListener('click', () => {
        const name = prompt('Enter preset name:');
        if (name) {
            const sequence = Array.from(sequenceList.querySelectorAll('li')).map(li => li.dataset.command);
            localStorage.setItem(`preset_${name}`, JSON.stringify({ sequence }));
            showToast(`Preset "${name}" saved`, 'success');
        }
    });

    // --- KEYBOARD SHORTCUTS ---
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey || e.metaKey) {
            switch(e.key) {
                case 'e':
                    e.preventDefault();
                    runSequence();
                    break;
                case 'l':
                    e.preventDefault();
                    toggleLog();
                    break;
                case 'k':
                    e.preventDefault();
                    clearLogBtn.click();
                    break;
            }
        }
    });

    // --- INITIAL LOAD ---
    vendorSelect.addEventListener('change', () => fetchAvps(vendorSelect.value));
    fetchAvps(vendorSelect.value);
});
