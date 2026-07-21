// Step 2: Subtopic Research UI

let _currentSystemPrompt = '';
let _currentModel = '';

document.addEventListener('DOMContentLoaded', () => {
    initStep2();
});

async function initStep2() {
    await loadStep2Params();
    await loadStep2Data();

    document.getElementById('step2-run-all-btn').addEventListener('click', runAllResearch);
    document.getElementById('step2-save-params-btn').addEventListener('click', saveParams);
    document.getElementById('step2-temperature').addEventListener('input', (e) => {
        document.getElementById('temp-value').textContent = parseFloat(e.target.value).toFixed(1);
    });

    // Auto-save params on change
    document.getElementById('step2-model').addEventListener('change', () => {
        _currentModel = document.getElementById('step2-model').value;
        autoSaveParams();
    });
    document.getElementById('step2-temperature').addEventListener('change', () => autoSaveParams());
    document.getElementById('step2-max-tokens').addEventListener('change', () => autoSaveParams());

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

        _currentModel = params.model || 'gemini-2.5-flash-lite';
        document.getElementById('step2-temperature').value = params.temperature || 0.7;
        document.getElementById('temp-value').textContent = (params.temperature || 0.7).toFixed(1);
        document.getElementById('step2-max-tokens').value = params.max_tokens || 8192;
        document.getElementById('step2-system-prompt').value = params.system_prompt || '';
        _currentSystemPrompt = params.system_prompt || '';
    } catch (e) {
        console.error('Failed to load Step 2 params:', e);
    }
}

async function loadStep2Data() {
    try {
        const step2 = await API.get('/api/step/2/data');
        const step1 = await API.get('/api/step/1/data');
        const subtopics = step1.subtopics || [];

        // Show/hide controls
        const controlsCard = document.getElementById('step2-controls-card');
        controlsCard.style.display = subtopics.length > 0 ? 'block' : 'none';

        renderResearchBoxes(subtopics, step2.research_results || []);

        // Update run status if running
        const statusEl = document.getElementById('step2-run-status');
        if (step2.status === 'running') {
            statusEl.innerHTML = '<span class="spinner"></span> Researching...';
        }

        // Poll if any box is running
        const results = step2.research_results || [];
        if (results.some(r => r.status === 'running')) {
            startPolling();
        }
    } catch (e) {
        console.error('Failed to load Step 2 data:', e);
        showError(e.message);
    }
}

function renderResearchBoxes(subtopics, researchResults) {
    const container = document.getElementById('step2-results-container');

    if (subtopics.length === 0) {
        container.innerHTML = `
            <div class="card">
                <p style="color:var(--text-secondary)">
                    No subtopics to research yet. Go to Step 1 to generate your article outline first.
                </p>
            </div>
        `;
        return;
    }

    // Build a lookup by topic_id
    const resultLookup = {};
    for (const r of researchResults) {
        resultLookup[r.topic_id] = r;
    }

    container.innerHTML = subtopics.map(st => {
        const result = resultLookup[st.id] || { status: 'idle', research_summary: '', sources: [], error: null };
        const status = result.status || 'idle';
        const statusClass = status;
        const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);

        // Build the compiled user message that gets sent to Gemini (per-box, always visible)
        const compiledUserMessage = [
            `ARGUMENT TO PROVE: ${st.angle || ''}`,
            `WHAT TO DIG FOR: ${st.research_info || ''}`,
            `SEARCH: ${st.search_query || ''}`,
            `TITLE: ${st.title || ''}`,
            '',
            'Research this argument using Google Search. Document the facts as they fit the argument. Go beyond the obvious. Return the JSON object with your research summary and sources.'
        ].join('\n');

        let bodyHtml = '';
        let actionBtn = '';

        if (status === 'running') {
            bodyHtml = '<div style="padding:12px 0;"><span class="spinner"></span> Researching with Google Search...</div>';
            actionBtn = '';
        } else if (status === 'completed') {
            const summary = result.research_summary || '';
            const sources = result.sources || [];
            bodyHtml = `
                <div style="margin-bottom:12px;">
                    <span style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px;">Research Summary</span>
                    <div style="margin-top:4px; font-size:13px; line-height:1.6; color:var(--text); white-space:pre-wrap;">${escapeHtml(summary)}</div>
                </div>
                ${sources.length > 0 ? `
                <div style="margin-bottom:12px;">
                    <span style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px;">Sources (${sources.length})</span>
                    <div style="margin-top:4px; display:flex; flex-wrap:wrap; gap:6px;">
                        ${sources.map((s, i) => `
                            <a href="${escapeHtml(s.url || '#')}" target="_blank" rel="noopener"
                               style="display:inline-block; padding:4px 10px; background:var(--bg); border:1px solid var(--border); border-radius:4px; font-size:12px; color:var(--accent); text-decoration:none;"
                               title="${escapeHtml(s.url || '')}">
                               [${i + 1}] ${escapeHtml(s.title || s.url || 'Source')}
                            </a>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
            `;
            actionBtn = `<button class="secondary step2-run-btn" data-topic-id="${st.id}" style="font-size:12px;">🔄 Re-run</button>`;
        } else if (status === 'failed') {
            bodyHtml = `
                <div class="error-box" style="margin:8px 0;">
                    ${escapeHtml(result.error || 'Unknown error')}
                </div>
            `;
            actionBtn = `<button class="step2-run-btn" data-topic-id="${st.id}" style="font-size:12px;">🔁 Retry</button>`;
        } else {
            // idle
            bodyHtml = '';
            actionBtn = `<button class="step2-run-btn" data-topic-id="${st.id}" style="font-size:12px;">🔍 Research This</button>`;
        }

        const borderColor = status === 'completed' ? 'var(--success)' :
                           status === 'failed' ? 'var(--error)' :
                           status === 'running' ? 'var(--accent)' : 'var(--border)';

        return `
            <div class="card research-card" data-topic-id="${st.id}" style="border-left:3px solid ${borderColor};">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
                    <div style="display:flex; align-items:baseline; gap:10px;">
                        <span style="font-weight:700; color:var(--accent); font-size:14px; flex-shrink:0;">#${st.id}</span>
                        <span style="font-weight:600; font-size:15px; line-height:1.4;">${escapeHtml(st.title || '(untitled)')}</span>
                    </div>
                    <span class="status ${statusClass}">${statusLabel}</span>
                </div>
                <div style="margin-bottom:12px;">
                    <span style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px;">User Message (sent to Gemini)</span>
                    <pre style="margin:4px 0 0 0; font-size:11px; font-family:var(--mono); line-height:1.5; color:var(--text); background:var(--bg); padding:8px 10px; border-radius:4px; white-space:pre-wrap; overflow-x:auto;">${escapeHtml(compiledUserMessage)}</pre>
                </div>
                ${bodyHtml}
                <div style="margin-top:${bodyHtml ? '12' : '0'}px; display:flex; align-items:center; gap:8px;">
                    ${actionBtn}
                    <span class="step2-box-status" data-topic-id="${st.id}"></span>
                </div>
            </div>
        `;
    }).join('');

    // Wire up per-box buttons
    container.querySelectorAll('.step2-run-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const topicId = parseInt(btn.dataset.topicId);
            runSingleTopic(topicId);
        });
    });
}

async function runSingleTopic(topicId) {
    const card = document.querySelector(`.research-card[data-topic-id="${topicId}"]`);
    const btn = card.querySelector('.step2-run-btn');
    const statusEl = card.querySelector('.step2-box-status');

    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Running...';
    }
    if (statusEl) {
        statusEl.innerHTML = '<span class="spinner"></span>';
    }

    hideError();

    try {
        const result = await API.post(`/api/step/2/run-topic/${topicId}`, {});

        if (result.ok) {
            if (statusEl) {
                statusEl.innerHTML = '<span style="color:var(--success)">✓ Done</span>';
            }
            // Reload data to refresh display
            await loadStep2Data();
        } else {
            if (statusEl) {
                statusEl.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(result.error || 'Failed')}</span>`;
            }
            // Reload to show the per-box error
            await loadStep2Data();
        }
    } catch (e) {
        if (statusEl) {
            statusEl.innerHTML = `<span style="color:var(--error)">✗ ${escapeHtml(e.message)}</span>`;
        }
        await loadStep2Data();
    }
}

async function runAllResearch() {
    const btn = document.getElementById('step2-run-all-btn');
    const status = document.getElementById('step2-run-status');

    btn.disabled = true;
    btn.textContent = 'Running...';
    status.innerHTML = '<span class="spinner"></span> Researching all subtopics sequentially...';
    hideError();

    try {
        const result = await API.post('/api/step/2/run', {});

        if (result.ok) {
            status.innerHTML = '<span style="color:var(--success)">✓ All research completed</span>';
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
        btn.textContent = '🔍 Research All';
    }
}

async function autoSaveParams() {
    try {
        await API.put('/api/step/2/params', {
            model: _currentModel,
            temperature: parseFloat(document.getElementById('step2-temperature').value),
            max_tokens: parseInt(document.getElementById('step2-max-tokens').value),
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
            const results = step2.research_results || [];
            const stillRunning = results.some(r => r.status === 'running');

            // Reload to refresh the UI
            const step1 = await API.get('/api/step/1/data');
            renderResearchBoxes(step1.subtopics || [], results);

            const statusEl = document.getElementById('step2-run-status');
            if (stillRunning) {
                statusEl.innerHTML = '<span class="spinner"></span> Researching...';
            } else if (step2.status === 'completed') {
                statusEl.innerHTML = '<span style="color:var(--success)">✓ All research completed</span>';
                stopPolling();
            } else if (step2.status === 'partial') {
                statusEl.innerHTML = '<span style="color:var(--warning)">⚠ Partially complete — some topics still need research</span>';
                stopPolling();
            } else if (step2.status === 'failed') {
                statusEl.innerHTML = '<span style="color:var(--error)">✗ Research failed</span>';
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
