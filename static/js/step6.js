// Step 6: Image Generation UI

document.addEventListener('DOMContentLoaded', () => {
    initStep6();
});

async function initStep6() {
    await loadStep6Params();
    await loadStep6Data();

    document.getElementById('step6-run-all-btn').addEventListener('click', runAllImages);
    document.getElementById('step6-save-params-btn').addEventListener('click', saveParams);
    document.getElementById('step6-model').addEventListener('change', () => autoSaveParams());
    document.getElementById('step6-size').addEventListener('change', () => autoSaveParams());
    document.getElementById('step6-quality').addEventListener('change', () => autoSaveParams());
}

async function loadStep6Params() {
    try {
        const params = await API.get('/api/step/6/params');

        const modelSelect = document.getElementById('step6-model');
        modelSelect.innerHTML = (params.available_models || []).map(m =>
            `<option value="${m.id}" ${m.id === params.model ? 'selected' : ''}>${m.name}</option>`
        ).join('');

        const sizeSelect = document.getElementById('step6-size');
        sizeSelect.innerHTML = (params.available_sizes || []).map(s =>
            `<option value="${s.id}" ${s.id === params.size ? 'selected' : ''}>${s.name}</option>`
        ).join('');

        const qualitySelect = document.getElementById('step6-quality');
        qualitySelect.innerHTML = (params.available_qualities || []).map(q =>
            `<option value="${q.id}" ${q.id === params.quality ? 'selected' : ''}>${q.name}</option>`
        ).join('');
    } catch (e) {
        console.error('Failed to load Step 6 params:', e);
    }
}

async function loadStep6Data() {
    try {
        const step6 = await API.get('/api/step/6/data');
        const step5 = await API.get('/api/step/5/data');

        const step5Done = step5.status === 'completed' && step5.image_cards && step5.image_cards.length > 0;

        if (step5Done) {
            document.getElementById('step6-controls-card').style.display = 'block';
            document.getElementById('step6-gated-card').style.display = 'none';
        } else {
            document.getElementById('step6-controls-card').style.display = 'none';
            document.getElementById('step6-gated-card').style.display = 'block';
            document.getElementById('step6-gated-status').textContent =
                ' Step 5 must be completed with image cards. Run Step 5 first.';
        }

        if (step6.image_cards && step6.image_cards.length > 0) {
            renderImageCards(step6.image_cards);
        }

        const statusEl = document.getElementById('step6-run-status');
        if (step6.status === 'running') {
            statusEl.innerHTML = '<span class="spinner"></span> Generating images...';
            startPolling();
        }
    } catch (e) {
        console.error('Failed to load Step 6 data:', e);
        showError(e.message);
    }
}

function renderImageCards(cards) {
    const output = document.getElementById('step6-output');
    if (!cards || cards.length === 0) {
        output.innerHTML = '';
        return;
    }

    const cardHtml = cards.map(card => {
        const cid = card.id || 0;
        const status = card.status || 'idle';
        const borderColor = status === 'completed' ? 'var(--success)' :
                           status === 'failed' ? 'var(--error)' :
                           status === 'running' ? 'var(--accent)' : 'var(--border)';
        const statusLabel = status === 'completed' ? '✓ Generated' :
                           status === 'failed' ? '✗ Failed' :
                           status === 'running' ? '⏳ Generating...' : 'Ready';

        // Image body
        let bodyHtml = '';
        let actionBtn = '';
        if (status === 'running') {
            bodyHtml = '<div style="padding:12px 0; text-align:center;"><span class="spinner"></span> Calling OpenAI...</div>';
        } else if (status === 'completed') {
            bodyHtml = card.image_b64 ? `
                <div style="margin-bottom:8px;">
                    <img src="data:image/png;base64,${card.image_b64}" style="max-width:100%; border-radius:var(--radius); display:block;" />
                </div>
            ` : '';
            bodyHtml += `
                <div style="font-size:11px; font-weight:600; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">💬 Caption</div>
                <div style="font-size:14px; color:var(--text); line-height:1.6; font-style:italic; background:var(--surface); border-left:3px solid var(--accent); padding:8px 12px; border-radius:0 var(--radius) var(--radius) 0; margin-bottom:8px;">${escapeHtml(card.caption || '')}</div>
                <div style="font-size:11px; font-weight:600; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">🎨 Prompt</div>
                <div style="font-size:12px; color:var(--text-secondary); line-height:1.5; white-space:pre-wrap;">${escapeHtml(card.image_prompt || '')}</div>
            `;
            actionBtn = `<button class="secondary step6-gen-btn" data-card-id="${cid}" style="font-size:12px;">🔄 Regenerate</button>`;
        } else if (status === 'failed') {
            bodyHtml = `
                <div class="error-box" style="margin:8px 0;">${escapeHtml(card.error || 'Unknown error')}</div>
                <div style="font-size:12px; color:var(--text-secondary); margin-bottom:4px;"><strong>Caption:</strong> ${escapeHtml(card.caption || '')}</div>
                <div style="font-size:12px; color:var(--text-secondary);"><strong>Prompt:</strong> ${escapeHtml((card.image_prompt || '').substring(0, 200))}...</div>
            `;
            actionBtn = `<button class="step6-gen-btn" data-card-id="${cid}" style="font-size:12px;">🔁 Retry</button>`;
        } else {
            // idle
            bodyHtml = `
                <div style="font-size:11px; font-weight:600; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">💬 Caption</div>
                <div style="font-size:14px; color:var(--text); line-height:1.6; font-style:italic; background:var(--surface); border-left:3px solid var(--accent); padding:8px 12px; border-radius:0 var(--radius) var(--radius) 0; margin-bottom:8px;">${escapeHtml(card.caption || '')}</div>
                <div style="font-size:11px; font-weight:600; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">🎨 Prompt</div>
                <div style="font-size:12px; color:var(--text-secondary); line-height:1.5; white-space:pre-wrap;">${escapeHtml(card.image_prompt || '')}</div>
            `;
            actionBtn = `<button class="step6-gen-btn" data-card-id="${cid}" style="font-size:12px;">🖼 Generate</button>`;
        }

        return `
            <div class="card" style="border-left:3px solid ${borderColor}; margin-bottom:16px;">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="background:var(--accent); color:#fff; font-size:11px; font-weight:700; padding:2px 8px; border-radius:3px; text-transform:uppercase; letter-spacing:0.5px;">CARD #${cid}</span>
                        <span style="font-weight:600; font-size:14px;">Image ${cid}</span>
                    </div>
                    <span class="status ${status}" style="font-size:11px; font-weight:600;">${statusLabel}</span>
                </div>
                ${bodyHtml}
                <div style="margin-top:12px; display:flex; align-items:center; gap:8px;">
                    ${actionBtn}
                    <span class="step6-card-status" data-card-id="${cid}"></span>
                </div>
            </div>
        `;
    }).join('');

    output.innerHTML = `
        <div style="margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:12px; color:var(--text-secondary);">${cards.length} image card${cards.length !== 1 ? 's' : ''}</span>
        </div>
        ${cardHtml}
    `;

    // Wire up per-card buttons
    output.querySelectorAll('.step6-gen-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const cardId = parseInt(btn.dataset.cardId);
            generateSingleImage(cardId);
        });
    });
}

async function generateSingleImage(cardId) {
    const btn = document.querySelector(`.step6-gen-btn[data-card-id="${cardId}"]`);
    const cardStatus = document.querySelector(`.step6-card-status[data-card-id="${cardId}"]`);
    if (btn) { btn.disabled = true; btn.textContent = 'Generating...'; }
    if (cardStatus) cardStatus.innerHTML = '<span class="spinner"></span>';

    try {
        const result = await API.post(`/api/step/6/run-card/${cardId}`, {});
        if (result.ok) {
            if (cardStatus) cardStatus.innerHTML = '<span style="color:var(--success); font-size:11px;">✓ Done</span>';
            refreshCards();
        } else {
            if (cardStatus) cardStatus.innerHTML = `<span style="color:var(--error); font-size:11px;">✗ ${escapeHtml(result.error || 'Failed')}</span>`;
            showError(result.error);
        }
    } catch (e) {
        if (cardStatus) cardStatus.innerHTML = `<span style="color:var(--error); font-size:11px;">✗ ${escapeHtml(e.message)}</span>`;
        showError(e.message);
    } finally {
        if (btn) { btn.disabled = false; }
    }
}

async function runAllImages() {
    const btn = document.getElementById('step6-run-all-btn');
    const status = document.getElementById('step6-run-status');
    btn.disabled = true;
    btn.textContent = 'Generating...';
    status.innerHTML = '<span class="spinner"></span> Generating all images...';
    hideError();

    try {
        const result = await API.post('/api/step/6/run', {});
        if (result.ok) {
            status.innerHTML = '<span style="color:var(--success)">✓ All complete</span>';
        } else {
            status.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(result.error || 'Failed')}</span>`;
            showError(result.error);
        }
        refreshCards();
    } catch (e) {
        status.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(e.message)}</span>`;
        showError(e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '🖼 Generate All Images';
    }
}

async function refreshCards() {
    try {
        const step6 = await API.get('/api/step/6/data');
        if (step6.image_cards) {
            renderImageCards(step6.image_cards);
        }
    } catch (e) {
        console.error('Failed to refresh cards:', e);
    }
}

// --- Polling ---
let _pollTimer = null;

function startPolling() {
    if (_pollTimer) return;
    _pollTimer = setInterval(async () => {
        try {
            const step6 = await API.get('/api/step/6/data');
            const statusEl = document.getElementById('step6-run-status');
            if (step6.status === 'completed') {
                statusEl.innerHTML = '<span style="color:var(--success)">✓ All complete</span>';
                renderImageCards(step6.image_cards);
                stopPolling();
            } else if (step6.status === 'partial' || step6.status === 'running') {
                renderImageCards(step6.image_cards);
            } else if (step6.status === 'failed') {
                statusEl.innerHTML = `<span style="color:var(--error)">✗ Failed</span>`;
                renderImageCards(step6.image_cards);
                stopPolling();
            }
        } catch (e) {
            stopPolling();
        }
    }, 2000);
}

function stopPolling() {
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null; }
}

// --- Params ---
async function autoSaveParams() {
    try {
        await API.put('/api/step/6/params', {
            model: document.getElementById('step6-model').value,
            size: document.getElementById('step6-size').value,
            quality: document.getElementById('step6-quality').value,
        });
    } catch (e) {
        console.error('Auto-save params failed:', e);
    }
}

async function saveParams() {
    const btn = document.getElementById('step6-save-params-btn');
    const saveStatus = document.getElementById('step6-params-status');
    btn.disabled = true; btn.textContent = 'Saving...';
    try {
        await API.put('/api/step/6/params', {
            model: document.getElementById('step6-model').value,
            size: document.getElementById('step6-size').value,
            quality: document.getElementById('step6-quality').value,
        });
        saveStatus.innerHTML = '<span style="color:var(--success)">✓ Saved</span>';
        setTimeout(() => { saveStatus.innerHTML = ''; }, 2000);
    } catch (e) {
        saveStatus.innerHTML = `<span style="color:var(--error)">✗ ${e.message}</span>`;
    } finally {
        btn.disabled = false; btn.textContent = 'Save Parameters';
    }
}

// --- Error ---
function showError(message) {
    const el = document.getElementById('step6-error');
    el.style.display = 'block';
    el.innerHTML = `<div class="error-box">${escapeHtml(message)}</div>`;
}
function hideError() {
    const el = document.getElementById('step6-error');
    el.style.display = 'none'; el.innerHTML = '';
}
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
