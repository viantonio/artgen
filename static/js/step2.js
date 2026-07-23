// Step 2: Draft Writing UI

let _currentSystemPrompt = '';
let _currentModel = '';

document.addEventListener('DOMContentLoaded', () => {
    initStep2();
});

async function initStep2() {
    await loadStep2Params();
    await loadStep2Data();

    document.getElementById('step2-run-all-btn').addEventListener('click', runAllDrafts);
    document.getElementById('step2-save-params-btn').addEventListener('click', saveParams);
    document.getElementById('step2-temperature').addEventListener('input', (e) => {
        document.getElementById('temp-value').textContent = parseFloat(e.target.value).toFixed(1);
    });

    // Auto-save params on change
    document.getElementById('step2-model').addEventListener('change', () => {
        _currentModel = document.getElementById('step2-model').value;
        updateModelSpecificParams();
        autoSaveParams();
    });
    document.getElementById('step2-temperature').addEventListener('change', () => autoSaveParams());
    document.getElementById('step2-max-tokens').addEventListener('change', () => autoSaveParams());
    document.getElementById('step2-thinking-budget').addEventListener('change', () => autoSaveParams());
    document.getElementById('step2-effort').addEventListener('change', () => autoSaveParams());

    let systemPromptTimeout;
    document.getElementById('step2-system-prompt').addEventListener('input', () => {
        _currentSystemPrompt = document.getElementById('step2-system-prompt').value;
        clearTimeout(systemPromptTimeout);
        systemPromptTimeout = setTimeout(() => autoSaveParams(), 500);
    });
}

async function loadStep2Params() {
    try {
        const params = await API.get('/api/step/2/params');
        const modelSelect = document.getElementById('step2-model');
        const models = params.available_models || [];
        modelSelect.innerHTML = models.map(m =>
            `<option value="${m.id}" ${m.id === params.model ? 'selected' : ''}>${m.name}</option>`
        ).join('');

        _currentModel = params.model || 'claude-haiku-4-5';
        document.getElementById('step2-temperature').value = params.temperature || 1.0;
        document.getElementById('temp-value').textContent = (params.temperature || 1.0).toFixed(1);
        document.getElementById('step2-max-tokens').value = params.max_tokens || 4096;
        document.getElementById('step2-thinking-budget').value = params.thinking_budget || 1600;
        document.getElementById('step2-effort').value = params.effort || 'high';
        document.getElementById('step2-system-prompt').value = params.system_prompt || '';
        _currentSystemPrompt = params.system_prompt || '';
        updateModelSpecificParams();
    } catch (e) {
        console.error('Failed to load Step 2 params:', e);
    }
}

async function loadStep2Data() {
    try {
        const step2 = await API.get('/api/step/2/data');
        const step1 = await API.get('/api/step/1/data');
        const cards = step1.cards || [];

        // Show/hide controls
        const controlsCard = document.getElementById('step2-controls-card');
        controlsCard.style.display = cards.length > 0 ? 'block' : 'none';

        renderDraftBoxes(cards, step2.drafts || []);

        // Update run status if running
        const statusEl = document.getElementById('step2-run-status');
        if (step2.status === 'running') {
            statusEl.innerHTML = '<span class="spinner"></span> Drafting...';
        }

        // Poll if any box is running
        const drafts = step2.drafts || [];
        if (drafts.some(d => d.status === 'running')) {
            startPolling();
        }
    } catch (e) {
        console.error('Failed to load Step 2 data:', e);
        showError(e.message);
    }
}

function getTypeBadge(type) {
    const colors = {
        'beginning': { bg: '#2d1f6e', text: '#b4a0ff', label: 'Beginning' },
        'middle': { bg: '#1e3a5f', text: '#7ab7ef', label: 'Middle' },
        'end': { bg: '#1e5f3a', text: '#7aef9f', label: 'End' },
    };
    const c = colors[type] || colors['middle'];
    return `<span style="display:inline-block; padding:2px 8px; border-radius:3px; font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; background:${c.bg}; color:${c.text}; flex-shrink:0;">${c.label}</span>`;
}

function renderDraftBoxes(cards, drafts) {
    const container = document.getElementById('step2-results-container');

    if (cards.length === 0) {
        container.innerHTML = `
            <div class="card">
                <p style="color:var(--text-secondary)">
                    No outline cards to draft yet. Go to Step 1 to generate your article outline first.
                </p>
            </div>
        `;
        return;
    }

    // Build a lookup by card_id
    const draftLookup = {};
    for (const d of drafts) {
        draftLookup[d.card_id] = d;
    }

    container.innerHTML = cards.map(card => {
        const draft = draftLookup[card.id] || { status: 'idle', draft: '', error: null };
        const status = draft.status || 'idle';
        const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);

        let bodyHtml = '';
        let actionBtn = '';

        if (status === 'running') {
            bodyHtml = '<div style="padding:12px 0;"><span class="spinner"></span> Writing draft with extended thinking...</div>';
            actionBtn = '';
        } else if (status === 'completed') {
            const draftText = draft.draft || '';
            bodyHtml = `
                <div style="margin-bottom:12px;">
                    <span style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px;">Draft</span>
                    <div style="margin-top:4px; font-size:13px; line-height:1.7; color:var(--text); white-space:pre-wrap;">${escapeHtml(draftText)}</div>
                </div>
            `;
            actionBtn = `<button class="secondary step2-draft-btn" data-card-id="${card.id}" style="font-size:12px;">🔄 Re-draft</button>`;
        } else if (status === 'failed') {
            bodyHtml = `
                <div class="error-box" style="margin:8px 0;">
                    ${escapeHtml(draft.error || 'Unknown error')}
                </div>
            `;
            actionBtn = `<button class="step2-draft-btn" data-card-id="${card.id}" style="font-size:12px;">🔁 Retry</button>`;
        } else {
            // idle
            bodyHtml = `
                <div style="margin-bottom:8px;">
                    <span style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px;">Angle</span>
                    <p style="margin:2px 0 0 0; font-size:12px; line-height:1.5; color:var(--text-secondary);">${escapeHtml(card.angle || '—')}</p>
                </div>
            `;
            actionBtn = `<button class="step2-draft-btn" data-card-id="${card.id}" style="font-size:12px;">✍️ Draft This</button>`;
        }

        const borderColor = status === 'completed' ? 'var(--success)' :
                           status === 'failed' ? 'var(--error)' :
                           status === 'running' ? 'var(--accent)' : 'var(--border)';

        return `
            <div class="card draft-card" data-card-id="${card.id}" style="border-left:3px solid ${borderColor};">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
                    <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                        ${getTypeBadge(card.type)}
                        <span style="font-weight:600; font-size:15px; line-height:1.4;">${escapeHtml(card.title || '(untitled)')}</span>
                    </div>
                    <span class="status ${status}">${statusLabel}</span>
                </div>
                ${bodyHtml}
                <div style="margin-top:${bodyHtml ? '12' : '0'}px; display:flex; align-items:center; gap:8px;">
                    ${actionBtn}
                    <span class="step2-box-status" data-card-id="${card.id}"></span>
                </div>
            </div>
        `;
    }).join('');

    // Wire up per-box buttons
    container.querySelectorAll('.step2-draft-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const cardId = parseInt(btn.dataset.cardId);
            draftSingleCard(cardId);
        });
    });
}

async function draftSingleCard(cardId) {
    const card = document.querySelector(`.draft-card[data-card-id="${cardId}"]`);
    const btn = card.querySelector('.step2-draft-btn');
    const statusEl = card.querySelector('.step2-box-status');

    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Drafting...';
    }
    if (statusEl) {
        statusEl.innerHTML = '<span class="spinner"></span>';
    }

    hideError();

    try {
        const result = await API.post(`/api/step/2/run-card/${cardId}`, {});

        if (result.ok) {
            if (statusEl) {
                statusEl.innerHTML = '<span style="color:var(--success)">✓ Done</span>';
            }
            await loadStep2Data();
        } else {
            if (statusEl) {
                statusEl.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(result.error || 'Failed')}</span>`;
            }
            await loadStep2Data();
        }
    } catch (e) {
        if (statusEl) {
            statusEl.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(e.message)}</span>`;
        }
        await loadStep2Data();
    }
}

async function runAllDrafts() {
    const btn = document.getElementById('step2-run-all-btn');
    const status = document.getElementById('step2-run-status');

    btn.disabled = true;
    btn.textContent = 'Drafting...';
    status.innerHTML = '<span class="spinner"></span> Drafting all cards sequentially...';
    hideError();

    try {
        const result = await API.post('/api/step/2/run', {});

        if (result.ok) {
            status.innerHTML = '<span style="color:var(--success)">✓ All drafts completed</span>';
        } else {
            status.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(result.error || 'Unknown error')}</span>`;
            showError(result.error);
        }
        await loadStep2Data();
    } catch (e) {
        status.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(e.message)}</span>`;
        showError(e.message);
        await loadStep2Data();
    } finally {
        btn.disabled = false;
        btn.textContent = '✍️ Draft All';
    }
}

function updateModelSpecificParams() {
    const isHaiku = _currentModel.startsWith('claude-haiku');
    document.getElementById('step2-thinking-budget-group').style.display = isHaiku ? 'block' : 'none';
    document.getElementById('step2-effort-group').style.display = isHaiku ? 'none' : 'block';
    // Haiku requires temp = 1.0 for thinking
    if (isHaiku) {
        document.getElementById('step2-temperature').value = 1.0;
        document.getElementById('temp-value').textContent = '1.0';
    }
}

async function autoSaveParams() {
    try {
        await API.put('/api/step/2/params', {
            model: _currentModel,
            temperature: parseFloat(document.getElementById('step2-temperature').value),
            max_tokens: parseInt(document.getElementById('step2-max-tokens').value),
            thinking_budget: parseInt(document.getElementById('step2-thinking-budget').value),
            effort: document.getElementById('step2-effort').value,
            system_prompt: _currentSystemPrompt,
        });
    } catch (e) {
        console.error('Auto-save params failed:', e);
    }
}

async function saveParams() {
    const btn = document.getElementById('step2-save-params-btn');
    const status = document.getElementById('step2-params-status');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    _currentSystemPrompt = document.getElementById('step2-system-prompt').value;
    _currentModel = document.getElementById('step2-model').value;

    try {
        await API.put('/api/step/2/params', {
            model: _currentModel,
            temperature: parseFloat(document.getElementById('step2-temperature').value),
            max_tokens: parseInt(document.getElementById('step2-max-tokens').value),
            thinking_budget: parseInt(document.getElementById('step2-thinking-budget').value),
            effort: document.getElementById('step2-effort').value,
            system_prompt: _currentSystemPrompt,
        });
        status.innerHTML = '<span style="color:var(--success)">✓ Saved</span>';
        setTimeout(() => { status.innerHTML = ''; }, 2000);
    } catch (e) {
        status.innerHTML = `<span style="color:var(--error)">✗ ${e.message}</span>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save Parameters';
    }
}

// --- Polling ---

let _pollTimer = null;

function startPolling() {
    if (_pollTimer) return;
    _pollTimer = setInterval(async () => {
        try {
            const step2 = await API.get('/api/step/2/data');
            const drafts = step2.drafts || [];
            const stillRunning = drafts.some(d => d.status === 'running');

            const step1 = await API.get('/api/step/1/data');
            renderDraftBoxes(step1.cards || [], drafts);

            const statusEl = document.getElementById('step2-run-status');
            if (stillRunning) {
                statusEl.innerHTML = '<span class="spinner"></span> Drafting...';
            } else if (step2.status === 'completed') {
                statusEl.innerHTML = '<span style="color:var(--success)">✓ All drafts completed</span>';
                stopPolling();
            } else if (step2.status === 'partial') {
                statusEl.innerHTML = '<span style="color:var(--warning)">⚠ Partially complete — some cards still need drafting</span>';
                stopPolling();
            } else if (step2.status === 'failed') {
                statusEl.innerHTML = '<span style="color:var(--error)">✗ Drafting failed</span>';
                stopPolling();
            }
        } catch (e) {
            stopPolling();
        }
    }, 2000);
}

function stopPolling() {
    if (_pollTimer) {
        clearInterval(_pollTimer);
        _pollTimer = null;
    }
}

// --- Error display ---

function showError(message) {
    const errorDiv = document.getElementById('step2-error');
    errorDiv.style.display = 'block';
    errorDiv.innerHTML = `<div class="error-box">${escapeHtml(message)}</div>`;
}

function hideError() {
    const errorDiv = document.getElementById('step2-error');
    errorDiv.style.display = 'none';
    errorDiv.innerHTML = '';
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
