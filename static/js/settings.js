// Settings page logic

document.addEventListener('DOMContentLoaded', () => {
    loadSettings();

    document.getElementById('save-anthropic-btn').addEventListener('click', saveAnthropicKey);
    document.getElementById('validate-anthropic-btn').addEventListener('click', validateAnthropic);
    document.getElementById('save-gemini-btn').addEventListener('click', saveGeminiKey);
    document.getElementById('validate-gemini-btn').addEventListener('click', validateGemini);
    document.getElementById('reset-all-btn').addEventListener('click', resetAllData);
});

async function loadSettings() {
    try {
        const settings = await API.get('/api/settings');
        if (settings.anthropic_key) {
            document.getElementById('anthropic-key').value = settings.anthropic_key;
        }
        if (settings.gemini_key) {
            document.getElementById('gemini-key').value = settings.gemini_key;
        }
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

async function saveAnthropicKey() {
    const key = document.getElementById('anthropic-key').value;
    const btn = document.getElementById('save-anthropic-btn');
    btn.disabled = true;
    btn.textContent = 'Saving...';
    try {
        await API.put('/api/settings', { anthropic_key: key });
        btn.textContent = 'Saved!';
        setTimeout(() => { btn.disabled = false; btn.textContent = 'Save Key'; }, 1500);
    } catch (e) {
        btn.disabled = false;
        btn.textContent = 'Save Key';
        alert('Failed to save: ' + e.message);
    }
}

async function saveGeminiKey() {
    const key = document.getElementById('gemini-key').value;
    const btn = document.getElementById('save-gemini-btn');
    btn.disabled = true;
    btn.textContent = 'Saving...';
    try {
        await API.put('/api/settings', { gemini_key: key });
        btn.textContent = 'Saved!';
        setTimeout(() => { btn.disabled = false; btn.textContent = 'Save Key'; }, 1500);
    } catch (e) {
        btn.disabled = false;
        btn.textContent = 'Save Key';
        alert('Failed to save: ' + e.message);
    }
}

async function validateAnthropic() {
    const status = document.getElementById('anthropic-status');
    const btn = document.getElementById('validate-anthropic-btn');
    status.innerHTML = '<span class="spinner"></span> Testing...';
    btn.disabled = true;
    try {
        const result = await API.post('/api/settings/validate/anthropic', {});
        if (result.valid) {
            status.innerHTML = '<span style="color:var(--success)">✓ Valid — ' + result.model + '</span>';
        } else {
            status.innerHTML = '<span style="color:var(--error)">✗ ' + result.error + '</span>';
        }
    } catch (e) {
        status.innerHTML = '<span style="color:var(--error)">✗ ' + e.message + '</span>';
    }
    btn.disabled = false;
}

async function validateGemini() {
    const status = document.getElementById('gemini-status');
    const btn = document.getElementById('validate-gemini-btn');
    status.innerHTML = '<span class="spinner"></span> Testing...';
    btn.disabled = true;
    try {
        const result = await API.post('/api/settings/validate/gemini', {});
        if (result.valid) {
            status.innerHTML = '<span style="color:var(--success)">✓ Valid</span>';
        } else {
            status.innerHTML = '<span style="color:var(--error)">✗ ' + result.error + '</span>';
        }
    } catch (e) {
        status.innerHTML = '<span style="color:var(--error)">✗ ' + e.message + '</span>';
    }
    btn.disabled = false;
}

async function resetAllData() {
    const status = document.getElementById('reset-status');
    const btn = document.getElementById('reset-all-btn');

    if (!confirm('DELETE ALL DATA?\n\nThis will permanently wipe every project, log, and setting. Your API keys will be lost. There is no undo.\n\nAre you sure?')) {
        return;
    }
    if (!confirm('Final warning: type OK in the next dialog to confirm.')) {
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Resetting...';
    status.innerHTML = '<span class="spinner"></span> Wiping all data...';

    try {
        const result = await API.post('/api/reset', {});
        if (result.ok) {
            status.innerHTML = '<span style="color:var(--success)">✓ All data wiped. Reloading...</span>';
            // Clear key inputs
            document.getElementById('anthropic-key').value = '';
            document.getElementById('gemini-key').value = '';
            setTimeout(() => { location.reload(); }, 1500);
        } else {
            status.innerHTML = '<span style="color:var(--error)">✗ ' + result.error + '</span>';
            btn.disabled = false;
            btn.textContent = '🗑 Reset All Data';
        }
    } catch (e) {
        status.innerHTML = '<span style="color:var(--error)">✗ ' + e.message + '</span>';
        btn.disabled = false;
        btn.textContent = '🗑 Reset All Data';
    }
}
