// Step 5: Image Planning UI

let _currentSystemPrompt = '';
let _currentModel = '';

document.addEventListener('DOMContentLoaded', () => {
    initStep5();
});

async function initStep5() {
    await loadStep5Params();
    await loadStep5Data();

    document.getElementById('step5-run-btn').addEventListener('click', runStep5);
    document.getElementById('step5-save-params-btn').addEventListener('click', saveParams);
    document.getElementById('step5-temperature').addEventListener('input', (e) => {
        document.getElementById('temp-value').textContent = parseFloat(e.target.value).toFixed(1);
    });

    // Auto-save params on change
    document.getElementById('step5-model').addEventListener('change', () => {
        _currentModel = document.getElementById('step5-model').value;
        updateModelSpecificParams();
        autoSaveParams();
    });
    document.getElementById('step5-temperature').addEventListener('change', () => autoSaveParams());
    document.getElementById('step5-max-tokens').addEventListener('change', () => autoSaveParams());
    document.getElementById('step5-thinking-budget').addEventListener('change', () => autoSaveParams());
    document.getElementById('step5-effort').addEventListener('change', () => autoSaveParams());

    let systemPromptTimeout;
    document.getElementById('step5-system-prompt').addEventListener('input', () => {
        _currentSystemPrompt = document.getElementById('step5-system-prompt').value;
        clearTimeout(systemPromptTimeout);
        systemPromptTimeout = setTimeout(() => autoSaveParams(), 500);
    });

    // Image count change — auto-save and refresh user message preview
    document.getElementById('step5-image-count').addEventListener('change', async () => {
        await saveImageCount();
        loadUserMessage();  // refresh preview with new count
    });
}

async function loadStep5Params() {
    try {
        const params = await API.get('/api/step/5/params');
        const modelSelect = document.getElementById('step5-model');
        const models = params.available_models || [];
        modelSelect.innerHTML = models.map(m =>
            `<option value="${m.id}" ${m.id === params.model ? 'selected' : ''}>${m.name}</option>`
        ).join('');

        _currentModel = params.model || 'claude-haiku-4-5';
        document.getElementById('step5-temperature').value = params.temperature || 1.0;
        document.getElementById('temp-value').textContent = (params.temperature || 1.0).toFixed(1);
        document.getElementById('step5-max-tokens').value = params.max_tokens || 8192;
        document.getElementById('step5-thinking-budget').value = params.thinking_budget || 1600;
        document.getElementById('step5-effort').value = params.effort || 'high';
        document.getElementById('step5-system-prompt').value = params.system_prompt || '';
        _currentSystemPrompt = params.system_prompt || '';
        updateModelSpecificParams();
    } catch (e) {
        console.error('Failed to load Step 5 params:', e);
    }
}

async function loadStep5Data() {
    try {
        const step5 = await API.get('/api/step/5/data');
        const step4 = await API.get('/api/step/4/data');

        // Set image count from data
        const countInput = document.getElementById('step5-image-count');
        if (countInput) {
            countInput.value = step5.image_count || 3;
        }

        // Check if Step 4 is fully done
        const step4Done = step4.status === 'completed' && step4.styled_article && step4.styled_article.trim();

        const controlsCard = document.getElementById('step5-controls-card');
        const previewCard = document.getElementById('step5-preview-card');
        const gatedCard = document.getElementById('step5-gated-card');
        const outputCard = document.getElementById('step5-output-card');

        if (step4Done) {
            controlsCard.style.display = 'block';
            previewCard.style.display = 'block';
            gatedCard.style.display = 'none';
            outputCard.style.display = 'block';

            // Load user message preview
            loadUserMessage();
        } else {
            controlsCard.style.display = 'none';
            previewCard.style.display = 'none';
            gatedCard.style.display = 'block';
            outputCard.style.display = 'none';

            if (!step4.styled_article || !step4.styled_article.trim()) {
                document.getElementById('step5-gated-status').textContent =
                    ' No article from Step 4 yet. Run Step 4 (Style Rewrite) first.';
            } else if (step4.status === 'running') {
                document.getElementById('step5-gated-status').textContent =
                    ' Step 4 is currently running. Wait for it to complete.';
            } else if (step4.status === 'failed') {
                document.getElementById('step5-gated-status').textContent =
                    ' Step 4 failed. Go back and re-run Step 4.';
            } else {
                document.getElementById('step5-gated-status').textContent =
                    ` Step 4 status is "${step4.status}" — waiting for completion.`;
            }
        }

        // Render existing image cards if any
        if (step5.image_cards && step5.image_cards.length > 0) {
            renderImageCards(step5.image_cards);
        }

        // Update run status if running
        const statusEl = document.getElementById('step5-run-status');
        if (step5.status === 'running') {
            statusEl.innerHTML = '<span class="spinner"></span> Planning images...';
            startPolling();
        }
    } catch (e) {
        console.error('Failed to load Step 5 data:', e);
        showError(e.message);
    }
}

async function loadUserMessage() {
    try {
        const result = await API.get('/api/step/5/user-message');
        const preview = document.getElementById('step5-user-message-preview');
        if (result.user_message) {
            preview.textContent = result.user_message;
        } else if (result.warning) {
            preview.innerHTML = `<span style="color:var(--warning)">${escapeHtml(result.warning)}</span>`;
        }
    } catch (e) {
        console.error('Failed to load user message preview:', e);
        document.getElementById('step5-user-message-preview').textContent =
            '(Could not load preview — Step 4 article not available)';
    }
}

function renderImageCards(cards, stepStatus) {
    const outputCard = document.getElementById('step5-output-card');
    const output = document.getElementById('step5-output');
    outputCard.style.display = 'block';

    if (stepStatus === 'running') {
        output.innerHTML = '<div style="padding:20px 0; text-align:center;"><span class="spinner"></span> Planning images with extended thinking...</div>';
        return;
    }

    if (stepStatus === 'failed') {
        output.innerHTML = `<div class="error-box">Image planning failed. Check the error message above and try again.</div>`;
        return;
    }

    if (!cards || cards.length === 0) {
        output.innerHTML = '<p style="color:var(--text-secondary)">Click "Plan Images" to analyze the article and generate image cards.</p>';
        return;
    }

    const cardHtml = cards.map(card => {
        const cardId = card.id || 0;
        const cardStatus = card.status || 'completed';
        const borderColor = cardStatus === 'completed' ? 'var(--success)' :
                           cardStatus === 'failed' ? 'var(--error)' : 'var(--border)';
        const statusLabel = cardStatus === 'completed' ? '✓ Planned' :
                           cardStatus === 'failed' ? '✗ Failed' : cardStatus;

        return `
            <div class="card" style="border-left:3px solid ${borderColor}; margin-bottom:16px;">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <span style="
                            background:var(--accent);
                            color:#fff;
                            font-size:11px;
                            font-weight:700;
                            padding:2px 8px;
                            border-radius:3px;
                            text-transform:uppercase;
                            letter-spacing:0.5px;
                        ">CARD #${cardId}</span>
                        <span style="font-weight:600; font-size:14px;">Image ${cardId}</span>
                    </div>
                    <span class="status ${cardStatus}" style="font-size:11px; font-weight:600;">${statusLabel}</span>
                </div>

                <div style="margin-bottom:10px;">
                    <div style="font-size:11px; font-weight:600; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">📍 Anchor Text (image goes after this)</div>
                    <div style="
                        font-size:13px;
                        color:var(--text);
                        line-height:1.6;
                        background:var(--surface);
                        border-left:3px solid var(--accent);
                        padding:8px 12px;
                        border-radius:0 var(--radius) var(--radius) 0;
                        font-style:italic;
                    ">"${escapeHtml(card.anchor_text || '')}"</div>
                </div>

                <div style="margin-bottom:10px;">
                    <div style="font-size:11px; font-weight:600; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">💬 Caption</div>
                    <div style="
                        font-size:14px;
                        color:var(--text);
                        line-height:1.6;
                        font-style:italic;
                        background:var(--surface);
                        border-left:3px solid var(--accent);
                        padding:8px 12px;
                        border-radius:0 var(--radius) var(--radius) 0;
                    ">${escapeHtml(card.caption || '')}</div>
                </div>

                <div style="margin-bottom:10px;">
                    <div style="font-size:11px; font-weight:600; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">🎨 Image Prompt</div>
                    <div style="
                        font-size:13px;
                        color:var(--text);
                        line-height:1.6;
                        white-space:pre-wrap;
                        background:var(--surface);
                        padding:10px 12px;
                        border-radius:var(--radius);
                    ">${escapeHtml(card.image_prompt || '')}</div>
                </div>

                ${card.rationale ? `
                <div>
                    <div style="font-size:11px; font-weight:600; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">💡 Rationale</div>
                    <div style="font-size:12px; color:var(--text-secondary); line-height:1.5;">${escapeHtml(card.rationale)}</div>
                </div>
                ` : ''}
            </div>
        `;
    }).join('');

    output.innerHTML = `
        <div style="margin-bottom:16px; display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:12px; color:var(--text-secondary);">${cards.length} image card${cards.length !== 1 ? 's' : ''}</span>
            <span style="font-size:12px; color:var(--success); font-weight:600;">✓ Planning Complete</span>
        </div>
        ${cardHtml}
    `;
}

async function saveImageCount() {
    const imageCount = parseInt(document.getElementById('step5-image-count').value) || 3;
    try {
        await API.put('/api/step/5/data', {
            image_count: imageCount,
            image_cards: [],
            status: 'idle',
            error: null,
        });
    } catch (e) {
        console.error('Failed to save image count:', e);
    }
}

async function runStep5() {
    const btn = document.getElementById('step5-run-btn');
    const status = document.getElementById('step5-run-status');

    btn.disabled = true;
    btn.textContent = 'Planning...';
    status.innerHTML = '<span class="spinner"></span> Calling Anthropic API...';
    hideError();

    // Show output card with spinner
    const outputCard = document.getElementById('step5-output-card');
    outputCard.style.display = 'block';
    document.getElementById('step5-output').innerHTML =
        '<div style="padding:20px 0; text-align:center;"><span class="spinner"></span> Planning images with extended thinking...</div>';

    try {
        const result = await API.post('/api/step/5/run', {});

        if (result.ok && result.image_cards) {
            status.innerHTML = '<span style="color:var(--success)">✓ Completed</span>';
            renderImageCards(result.image_cards);
        } else {
            status.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(result.error || 'Unknown error')}</span>`;
            showError(result.error);
            renderImageCards(null, 'failed');
        }
    } catch (e) {
        status.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(e.message)}</span>`;
        showError(e.message);
        renderImageCards(null, 'failed');
    } finally {
        btn.disabled = false;
        btn.textContent = '🎯 Plan Images';
    }
}

function updateModelSpecificParams() {
    const isHaiku = _currentModel.startsWith('claude-haiku');
    document.getElementById('step5-thinking-budget-group').style.display = isHaiku ? 'block' : 'none';
    document.getElementById('step5-effort-group').style.display = isHaiku ? 'none' : 'block';
    // Haiku requires temp = 1.0 for thinking
    if (isHaiku) {
        document.getElementById('step5-temperature').value = 1.0;
        document.getElementById('temp-value').textContent = '1.0';
    }
}

async function autoSaveParams() {
    try {
        await API.put('/api/step/5/params', {
            model: _currentModel,
            temperature: parseFloat(document.getElementById('step5-temperature').value),
            max_tokens: parseInt(document.getElementById('step5-max-tokens').value),
            thinking_budget: parseInt(document.getElementById('step5-thinking-budget').value),
            effort: document.getElementById('step5-effort').value,
            system_prompt: _currentSystemPrompt,
        });
    } catch (e) {
        console.error('Auto-save params failed:', e);
    }
}

async function saveParams() {
    const btn = document.getElementById('step5-save-params-btn');
    const saveStatus = document.getElementById('step5-params-status');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    _currentSystemPrompt = document.getElementById('step5-system-prompt').value;
    _currentModel = document.getElementById('step5-model').value;

    try {
        await API.put('/api/step/5/params', {
            model: _currentModel,
            temperature: parseFloat(document.getElementById('step5-temperature').value),
            max_tokens: parseInt(document.getElementById('step5-max-tokens').value),
            thinking_budget: parseInt(document.getElementById('step5-thinking-budget').value),
            effort: document.getElementById('step5-effort').value,
            system_prompt: _currentSystemPrompt,
        });
        saveStatus.innerHTML = '<span style="color:var(--success)">✓ Saved</span>';
        setTimeout(() => { saveStatus.innerHTML = ''; }, 2000);
    } catch (e) {
        saveStatus.innerHTML = `<span style="color:var(--error)">✗ ${e.message}</span>`;
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
            const step5 = await API.get('/api/step/5/data');
            const statusEl = document.getElementById('step5-run-status');

            if (step5.status === 'completed') {
                statusEl.innerHTML = '<span style="color:var(--success)">✓ Completed</span>';
                renderImageCards(step5.image_cards);
                stopPolling();
            } else if (step5.status === 'failed') {
                statusEl.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(step5.error || 'Failed')}</span>`;
                renderImageCards(null, 'failed');
                stopPolling();
            } else if (step5.status === 'running') {
                statusEl.innerHTML = '<span class="spinner"></span> Planning images...';
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
    const errorDiv = document.getElementById('step5-error');
    errorDiv.style.display = 'block';
    errorDiv.innerHTML = `<div class="error-box">${escapeHtml(message)}</div>`;
}

function hideError() {
    const errorDiv = document.getElementById('step5-error');
    errorDiv.style.display = 'none';
    errorDiv.innerHTML = '';
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
