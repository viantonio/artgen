// Step 3: Article Synthesis UI

let _currentSystemPrompt = '';
let _currentModel = '';

document.addEventListener('DOMContentLoaded', () => {
    initStep3();
});

async function initStep3() {
    await loadStep3Params();
    await loadStep3Data();

    document.getElementById('step3-run-btn').addEventListener('click', runStep3);
    document.getElementById('step3-save-params-btn').addEventListener('click', saveParams);
    document.getElementById('step3-temperature').addEventListener('input', (e) => {
        document.getElementById('temp-value').textContent = parseFloat(e.target.value).toFixed(1);
    });

    // Auto-save params on change
    document.getElementById('step3-model').addEventListener('change', () => {
        _currentModel = document.getElementById('step3-model').value;
        updateModelSpecificParams();
        autoSaveParams();
    });
    document.getElementById('step3-temperature').addEventListener('change', () => autoSaveParams());
    document.getElementById('step3-max-tokens').addEventListener('change', () => autoSaveParams());
    document.getElementById('step3-thinking-budget').addEventListener('change', () => autoSaveParams());
    document.getElementById('step3-effort').addEventListener('change', () => autoSaveParams());

    let systemPromptTimeout;
    document.getElementById('step3-system-prompt').addEventListener('input', () => {
        _currentSystemPrompt = document.getElementById('step3-system-prompt').value;
        clearTimeout(systemPromptTimeout);
        systemPromptTimeout = setTimeout(() => autoSaveParams(), 500);
    });
}

async function loadStep3Params() {
    try {
        const params = await API.get('/api/step/3/params');
        const modelSelect = document.getElementById('step3-model');
        const models = params.available_models || [];
        modelSelect.innerHTML = models.map(m =>
            `<option value="${m.id}" ${m.id === params.model ? 'selected' : ''}>${m.name}</option>`
        ).join('');

        _currentModel = params.model || 'claude-haiku-4-5';
        document.getElementById('step3-temperature').value = params.temperature || 1.0;
        document.getElementById('temp-value').textContent = (params.temperature || 1.0).toFixed(1);
        document.getElementById('step3-max-tokens').value = params.max_tokens || 8192;
        document.getElementById('step3-thinking-budget').value = params.thinking_budget || 1600;
        document.getElementById('step3-effort').value = params.effort || 'high';
        document.getElementById('step3-system-prompt').value = params.system_prompt || '';
        _currentSystemPrompt = params.system_prompt || '';
        updateModelSpecificParams();
    } catch (e) {
        console.error('Failed to load Step 3 params:', e);
    }
}

async function loadStep3Data() {
    try {
        const step3 = await API.get('/api/step/3/data');
        const step2 = await API.get('/api/step/2/data');
        const drafts = step2.drafts || [];

        // Check if Step 2 is fully done
        const allCompleted = drafts.length > 0 && drafts.every(d => d.status === 'completed');
        const anyFailed = drafts.some(d => d.status === 'failed');

        const controlsCard = document.getElementById('step3-controls-card');
        const gatedCard = document.getElementById('step3-gated-card');
        const outputCard = document.getElementById('step3-output-card');

        if (allCompleted) {
            controlsCard.style.display = 'block';
            gatedCard.style.display = 'none';
            outputCard.style.display = 'block';
        } else {
            controlsCard.style.display = 'none';
            gatedCard.style.display = 'block';
            outputCard.style.display = 'none';

            if (drafts.length === 0) {
                document.getElementById('step3-gated-status').textContent =
                    'No drafts exist yet. Go to Step 2 and run the draft writer.';
            } else if (anyFailed) {
                const failed = drafts.filter(d => d.status === 'failed').map(d => d.card_title || `Card #${d.card_id}`);
                document.getElementById('step3-gated-status').innerHTML =
                    `<br><br><strong>Some drafts failed:</strong> ${escapeHtml(failed.join(', '))}<br>Go back to Step 2 and re-draft the failed cards.`;
            } else {
                const pending = drafts.filter(d => d.status !== 'completed').length;
                document.getElementById('step3-gated-status').textContent =
                    `${pending} of ${drafts.length} drafts still pending.`;
            }
        }

        // Render existing article if any
        if (step3.draft_article) {
            renderArticle(step3.draft_article, step3.status);
        }

        // Update run status if running
        const statusEl = document.getElementById('step3-run-status');
        if (step3.status === 'running') {
            statusEl.innerHTML = '<span class="spinner"></span> Synthesizing article...';
            // Poll until done
            startPolling();
        }
    } catch (e) {
        console.error('Failed to load Step 3 data:', e);
        showError(e.message);
    }
}

function renderArticle(articleText, status) {
    const outputCard = document.getElementById('step3-output-card');
    const output = document.getElementById('step3-output');
    outputCard.style.display = 'block';

    const wordCount = articleText ? articleText.split(/\s+/).length : 0;

    if (status === 'running') {
        output.innerHTML = '<div style="padding:20px 0; text-align:center;"><span class="spinner"></span> Synthesizing article with extended thinking...</div>';
        return;
    }

    if (status === 'failed') {
        output.innerHTML = `<div class="error-box">Synthesis failed. Check the error message above and try again.</div>`;
        return;
    }

    if (!articleText) {
        output.innerHTML = '<p style="color:var(--text-secondary)">Click "Synthesize Article" to generate the final draft.</p>';
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

async function runStep3() {
    const btn = document.getElementById('step3-run-btn');
    const status = document.getElementById('step3-run-status');

    btn.disabled = true;
    btn.textContent = 'Synthesizing...';
    status.innerHTML = '<span class="spinner"></span> Calling Anthropic API...';
    hideError();

    // Show output card with spinner
    const outputCard = document.getElementById('step3-output-card');
    outputCard.style.display = 'block';
    document.getElementById('step3-output').innerHTML =
        '<div style="padding:20px 0; text-align:center;"><span class="spinner"></span> Synthesizing article with extended thinking...</div>';

    try {
        const result = await API.post('/api/step/3/run', {});

        if (result.ok && result.draft_article) {
            status.innerHTML = '<span style="color:var(--success)">✓ Completed</span>';
            renderArticle(result.draft_article, 'completed');
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
        btn.textContent = '✍️ Synthesize Article';
    }
}

function updateModelSpecificParams() {
    const isHaiku = _currentModel.startsWith('claude-haiku');
    document.getElementById('step3-thinking-budget-group').style.display = isHaiku ? 'block' : 'none';
    document.getElementById('step3-effort-group').style.display = isHaiku ? 'none' : 'block';
    // Haiku requires temp = 1.0 for thinking
    if (isHaiku) {
        document.getElementById('step3-temperature').value = 1.0;
        document.getElementById('temp-value').textContent = '1.0';
    }
}

async function autoSaveParams() {
    try {
        await API.put('/api/step/3/params', {
            model: _currentModel,
            temperature: parseFloat(document.getElementById('step3-temperature').value),
            max_tokens: parseInt(document.getElementById('step3-max-tokens').value),
            thinking_budget: parseInt(document.getElementById('step3-thinking-budget').value),
            effort: document.getElementById('step3-effort').value,
            system_prompt: _currentSystemPrompt,
        });
    } catch (e) {
        console.error('Auto-save params failed:', e);
    }
}

async function saveParams() {
    const btn = document.getElementById('step3-save-params-btn');
    const saveStatus = document.getElementById('step3-params-status');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    _currentSystemPrompt = document.getElementById('step3-system-prompt').value;
    _currentModel = document.getElementById('step3-model').value;

    try {
        await API.put('/api/step/3/params', {
            model: _currentModel,
            temperature: parseFloat(document.getElementById('step3-temperature').value),
            max_tokens: parseInt(document.getElementById('step3-max-tokens').value),
            thinking_budget: parseInt(document.getElementById('step3-thinking-budget').value),
            effort: document.getElementById('step3-effort').value,
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
            const step3 = await API.get('/api/step/3/data');
            const statusEl = document.getElementById('step3-run-status');

            if (step3.status === 'completed') {
                statusEl.innerHTML = '<span style="color:var(--success)">✓ Completed</span>';
                renderArticle(step3.draft_article, 'completed');
                stopPolling();
            } else if (step3.status === 'failed') {
                statusEl.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(step3.error || 'Failed')}</span>`;
                renderArticle(null, 'failed');
                stopPolling();
            } else if (step3.status === 'running') {
                statusEl.innerHTML = '<span class="spinner"></span> Synthesizing article...';
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
    const errorDiv = document.getElementById('step3-error');
    errorDiv.style.display = 'block';
    errorDiv.innerHTML = `<div class="error-box">${escapeHtml(message)}</div>`;
}

function hideError() {
    const errorDiv = document.getElementById('step3-error');
    errorDiv.style.display = 'none';
    errorDiv.innerHTML = '';
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
