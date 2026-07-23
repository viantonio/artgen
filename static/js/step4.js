// Step 4: Style Rewrite UI

let _currentSystemPrompt = '';
let _currentModel = '';

document.addEventListener('DOMContentLoaded', () => {
    initStep4();
});

async function initStep4() {
    await loadStep4Params();
    await loadStep4Data();

    document.getElementById('step4-run-btn').addEventListener('click', runStep4);
    document.getElementById('step4-save-params-btn').addEventListener('click', saveParams);
    document.getElementById('step4-temperature').addEventListener('input', (e) => {
        document.getElementById('temp-value').textContent = parseFloat(e.target.value).toFixed(1);
    });

    // Auto-save params on change
    document.getElementById('step4-model').addEventListener('change', () => {
        _currentModel = document.getElementById('step4-model').value;
        updateModelSpecificParams();
        autoSaveParams();
    });
    document.getElementById('step4-temperature').addEventListener('change', () => autoSaveParams());
    document.getElementById('step4-max-tokens').addEventListener('change', () => autoSaveParams());
    document.getElementById('step4-thinking-budget').addEventListener('change', () => autoSaveParams());
    document.getElementById('step4-effort').addEventListener('change', () => autoSaveParams());

    let systemPromptTimeout;
    document.getElementById('step4-system-prompt').addEventListener('input', () => {
        _currentSystemPrompt = document.getElementById('step4-system-prompt').value;
        clearTimeout(systemPromptTimeout);
        systemPromptTimeout = setTimeout(() => autoSaveParams(), 500);
    });
}

async function loadStep4Params() {
    try {
        const params = await API.get('/api/step/4/params');
        const modelSelect = document.getElementById('step4-model');
        const models = params.available_models || [];
        modelSelect.innerHTML = models.map(m =>
            `<option value="${m.id}" ${m.id === params.model ? 'selected' : ''}>${m.name}</option>`
        ).join('');

        _currentModel = params.model || 'claude-haiku-4-5';
        document.getElementById('step4-temperature').value = params.temperature || 1.0;
        document.getElementById('temp-value').textContent = (params.temperature || 1.0).toFixed(1);
        document.getElementById('step4-max-tokens').value = params.max_tokens || 8192;
        document.getElementById('step4-thinking-budget').value = params.thinking_budget || 1600;
        document.getElementById('step4-effort').value = params.effort || 'high';
        document.getElementById('step4-system-prompt').value = params.system_prompt || '';
        _currentSystemPrompt = params.system_prompt || '';
        updateModelSpecificParams();
    } catch (e) {
        console.error('Failed to load Step 4 params:', e);
    }
}

async function loadStep4Data() {
    try {
        const step4 = await API.get('/api/step/4/data');
        const step3 = await API.get('/api/step/3/data');

        // Check if Step 3 is fully done
        const step3Done = step3.status === 'completed' && step3.draft_article && step3.draft_article.trim();

        const controlsCard = document.getElementById('step4-controls-card');
        const previewCard = document.getElementById('step4-preview-card');
        const gatedCard = document.getElementById('step4-gated-card');
        const outputCard = document.getElementById('step4-output-card');

        if (step3Done) {
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

            if (!step3.draft_article || !step3.draft_article.trim()) {
                document.getElementById('step4-gated-status').textContent =
                    ' No article from Step 3 yet. Run Step 3 (Article Synthesis) first.';
            } else if (step3.status === 'running') {
                document.getElementById('step4-gated-status').textContent =
                    ' Step 3 is currently running. Wait for it to complete.';
            } else if (step3.status === 'failed') {
                document.getElementById('step4-gated-status').textContent =
                    ' Step 3 failed. Go back and re-run Step 3.';
            } else {
                document.getElementById('step4-gated-status').textContent =
                    ` Step 3 status is "${step3.status}" — waiting for completion.`;
            }
        }

        // Render existing styled article if any
        if (step4.styled_article) {
            renderArticle(step4.styled_article, step4.status);
        }

        // Update run status if running
        const statusEl = document.getElementById('step4-run-status');
        if (step4.status === 'running') {
            statusEl.innerHTML = '<span class="spinner"></span> Rewriting article...';
            startPolling();
        }
    } catch (e) {
        console.error('Failed to load Step 4 data:', e);
        showError(e.message);
    }
}

async function loadUserMessage() {
    try {
        const result = await API.get('/api/step/4/user-message');
        const preview = document.getElementById('step4-user-message-preview');
        if (result.user_message) {
            preview.textContent = result.user_message;
        } else if (result.warning) {
            preview.innerHTML = `<span style="color:var(--warning)">${escapeHtml(result.warning)}</span>`;
        }
    } catch (e) {
        console.error('Failed to load user message preview:', e);
        document.getElementById('step4-user-message-preview').textContent =
            '(Could not load preview — Step 3 article not available)';
    }
}

function renderArticle(articleText, status) {
    const outputCard = document.getElementById('step4-output-card');
    const output = document.getElementById('step4-output');
    outputCard.style.display = 'block';

    const wordCount = articleText ? articleText.split(/\s+/).length : 0;

    if (status === 'running') {
        output.innerHTML = '<div style="padding:20px 0; text-align:center;"><span class="spinner"></span> Rewriting article with extended thinking...</div>';
        return;
    }

    if (status === 'failed') {
        output.innerHTML = `<div class="error-box">Style rewrite failed. Check the error message above and try again.</div>`;
        return;
    }

    if (!articleText) {
        output.innerHTML = '<p style="color:var(--text-secondary)">Click "Rewrite Article" to generate the styled version.</p>';
        return;
    }

    output.innerHTML = `
        <div style="margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:12px; color:var(--text-secondary);">${wordCount.toLocaleString()} words</span>
            <span style="font-size:12px; color:var(--success); font-weight:600;">✓ Completed</span>
        </div>
        <div class="article-content" style="
            font-size:15px;
            line-height:1.8;
            color:var(--text);
            white-space:pre-wrap;
            max-height:none;
            overflow:visible;
        ">${escapeHtml(articleText)}</div>
    `;
}

async function runStep4() {
    const btn = document.getElementById('step4-run-btn');
    const status = document.getElementById('step4-run-status');

    btn.disabled = true;
    btn.textContent = 'Rewriting...';
    status.innerHTML = '<span class="spinner"></span> Calling Anthropic API...';
    hideError();

    // Show output card with spinner
    const outputCard = document.getElementById('step4-output-card');
    outputCard.style.display = 'block';
    document.getElementById('step4-output').innerHTML =
        '<div style="padding:20px 0; text-align:center;"><span class="spinner"></span> Rewriting article with extended thinking...</div>';

    try {
        const result = await API.post('/api/step/4/run', {});

        if (result.ok && result.styled_article) {
            status.innerHTML = '<span style="color:var(--success)">✓ Completed</span>';
            renderArticle(result.styled_article, 'completed');
        } else {
            status.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(result.error || 'Unknown error')}</span>`;
            showError(result.error);
            renderArticle(null, 'failed');
        }
    } catch (e) {
        status.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(e.message)}</span>`;
        showError(e.message);
        renderArticle(null, 'failed');
    } finally {
        btn.disabled = false;
        btn.textContent = '🎨 Rewrite Article';
    }
}

function updateModelSpecificParams() {
    const isHaiku = _currentModel.startsWith('claude-haiku');
    document.getElementById('step4-thinking-budget-group').style.display = isHaiku ? 'block' : 'none';
    document.getElementById('step4-effort-group').style.display = isHaiku ? 'none' : 'block';
    // Haiku requires temp = 1.0 for thinking
    if (isHaiku) {
        document.getElementById('step4-temperature').value = 1.0;
        document.getElementById('temp-value').textContent = '1.0';
    }
}

async function autoSaveParams() {
    try {
        await API.put('/api/step/4/params', {
            model: _currentModel,
            temperature: parseFloat(document.getElementById('step4-temperature').value),
            max_tokens: parseInt(document.getElementById('step4-max-tokens').value),
            thinking_budget: parseInt(document.getElementById('step4-thinking-budget').value),
            effort: document.getElementById('step4-effort').value,
            system_prompt: _currentSystemPrompt,
        });
    } catch (e) {
        console.error('Auto-save params failed:', e);
    }
}

async function saveParams() {
    const btn = document.getElementById('step4-save-params-btn');
    const saveStatus = document.getElementById('step4-params-status');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    _currentSystemPrompt = document.getElementById('step4-system-prompt').value;
    _currentModel = document.getElementById('step4-model').value;

    try {
        await API.put('/api/step/4/params', {
            model: _currentModel,
            temperature: parseFloat(document.getElementById('step4-temperature').value),
            max_tokens: parseInt(document.getElementById('step4-max-tokens').value),
            thinking_budget: parseInt(document.getElementById('step4-thinking-budget').value),
            effort: document.getElementById('step4-effort').value,
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
            const step4 = await API.get('/api/step/4/data');
            const statusEl = document.getElementById('step4-run-status');

            if (step4.status === 'completed') {
                statusEl.innerHTML = '<span style="color:var(--success)">✓ Completed</span>';
                renderArticle(step4.styled_article, 'completed');
                stopPolling();
            } else if (step4.status === 'failed') {
                statusEl.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(step4.error || 'Failed')}</span>`;
                renderArticle(null, 'failed');
                stopPolling();
            } else if (step4.status === 'running') {
                statusEl.innerHTML = '<span class="spinner"></span> Rewriting article...';
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
    const errorDiv = document.getElementById('step4-error');
    errorDiv.style.display = 'block';
    errorDiv.innerHTML = `<div class="error-box">${escapeHtml(message)}</div>`;
}

function hideError() {
    const errorDiv = document.getElementById('step4-error');
    errorDiv.style.display = 'none';
    errorDiv.innerHTML = '';
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
