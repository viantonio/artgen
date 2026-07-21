// Step 1: Subtopic Planning UI

let _currentSystemPrompt = '';
let _currentModel = '';

document.addEventListener('DOMContentLoaded', () => {
    initStep1();
});

async function initStep1() {
    await loadStep1Data();
    await loadStep1Params();

    document.getElementById('step1-run-btn').addEventListener('click', runStep1);
    document.getElementById('step1-save-params-btn').addEventListener('click', saveParams);
    document.getElementById('step1-temperature').addEventListener('input', (e) => {
        document.getElementById('temp-value').textContent = parseFloat(e.target.value).toFixed(1);
    });

    let briefTimeout;
    document.getElementById('step1-topic').addEventListener('input', () => {
        clearTimeout(briefTimeout);
        briefTimeout = setTimeout(() => {
            saveBriefAndCount();
            updatePromptPreview();
        }, 500);
    });
    document.getElementById('step1-count').addEventListener('change', () => {
        saveBriefAndCount();
        updatePromptPreview();
    });

    document.getElementById('step1-system-prompt').addEventListener('input', () => {
        _currentSystemPrompt = document.getElementById('step1-system-prompt').value;
        updatePromptPreview();
    });
    document.getElementById('step1-model').addEventListener('change', () => {
        _currentModel = document.getElementById('step1-model').value;
        updatePromptPreview();
    });
    document.getElementById('step1-temperature').addEventListener('change', () => updatePromptPreview());
    document.getElementById('step1-max-tokens').addEventListener('change', () => updatePromptPreview());

    updatePromptPreview();
}

async function loadStep1Data() {
    try {
        const data = await API.get('/api/step/1/data');
        document.getElementById('step1-topic').value = data.topic || '';
        document.getElementById('step1-count').value = data.subtopic_count || 5;

        if (data.subtopics && data.subtopics.length > 0) {
            renderSubtopics(data.subtopics);
        }

        const statusEl = document.getElementById('step1-run-status');
        if (data.status === 'running') {
            statusEl.innerHTML = '<span class="spinner"></span> Running...';
        }
        if (data.error && data.status === 'failed') {
            showError(data.error);
        }
    } catch (e) {
        console.error('Failed to load Step 1 data:', e);
    }
}

async function loadStep1Params() {
    try {
        const params = await API.get('/api/step/1/params');
        const modelSelect = document.getElementById('step1-model');
        const models = params.available_models || [];
        modelSelect.innerHTML = models.map(m =>
            `<option value="${m.id}" ${m.id === params.model ? 'selected' : ''}>${m.name}</option>`
        ).join('');

        _currentModel = params.model || 'claude-haiku-4-5';
        document.getElementById('step1-temperature').value = params.temperature || 1.0;
        document.getElementById('temp-value').textContent = (params.temperature || 1.0).toFixed(1);
        document.getElementById('step1-max-tokens').value = params.max_tokens || 4096;
        document.getElementById('step1-system-prompt').value = params.system_prompt || '';
        _currentSystemPrompt = params.system_prompt || '';
    } catch (e) {
        console.error('Failed to load Step 1 params:', e);
    }
}

async function saveBriefAndCount() {
    const brief = document.getElementById('step1-topic').value;
    const count = parseInt(document.getElementById('step1-count').value) || 5;
    try {
        const result = await API.put('/api/step/1/data', {
            topic: brief,
            subtopic_count: count,
            subtopics: [],
            status: 'idle',
            error: null,
        });
        if (!result.ok) {
            showError(result.error);
        } else {
            hideError();
        }
    } catch (e) {
        showError(e.message);
    }
}

function buildFullPrompt() {
    const brief = document.getElementById('step1-topic').value.trim() || '(no brief entered yet)';
    const count = parseInt(document.getElementById('step1-count').value) || 5;
    const systemPrompt = _currentSystemPrompt || '(no system prompt set)';

    // NOTE: minItems > 1 / maxItems not supported by Anthropic structured outputs.
    // Count is enforced via the user message text instead.
    const schema = JSON.stringify({
        type: "object",
        properties: {
            subtopics: {
                type: "array",
                items: {
                    type: "object",
                    properties: {
                        id: { type: "integer", description: "1-based index" },
                        title: { type: "string", description: "Sharp, clickable section headline" },
                        angle: { type: "string", description: "The argument this section makes — the claim we're advancing" },
                        research_info: { type: "string", description: "Evidence to back up this argument: data, history, expert opinion, case studies, accounts — whatever proves the claim" },
                        search_query: { type: "string", description: "Targeted search query (5-12 words) to find the strongest sources supporting this argument" }
                    },
                    required: ["id", "title", "angle", "research_info", "search_query"],
                    additionalProperties: false
                }
            }
        },
        required: ["subtopics"],
        additionalProperties: false
    }, null, 2);

    const userMessage = `BRIEF: ${brief}\n\nBased on the brief above, generate exactly ${count} subtopics that comprehensively cover the key arguments and themes described. For each subtopic, provide a title, angle, research_info, and search_query as specified in the output schema.\n\nRemember: each section must make an argument and back it up with evidence. Choose the type of evidence that best supports the claim — data, journalism, historical examples, expert analysis, personal accounts, whatever fits. Return ONLY valid JSON.`;

    return `=== SYSTEM PROMPT (sent as 'system' parameter) ===
${systemPrompt}

=== USER MESSAGE (sent as 'messages' content) ===
${userMessage}

=== OUTPUT JSON SCHEMA (sent as 'output_config.format') ===
${schema}`;
}

function updatePromptPreview() {
    const brief = document.getElementById('step1-topic').value.trim();
    const previewCard = document.getElementById('step1-preview-card');
    const previewEl = document.getElementById('step1-preview');

    if (brief) {
        previewCard.style.display = 'block';
        previewEl.textContent = buildFullPrompt();
    } else {
        previewCard.style.display = 'none';
    }
}

async function saveParams() {
    const btn = document.getElementById('step1-save-params-btn');
    const status = document.getElementById('step1-params-status');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    _currentSystemPrompt = document.getElementById('step1-system-prompt').value;
    _currentModel = document.getElementById('step1-model').value;

    try {
        await API.put('/api/step/1/params', {
            model: _currentModel,
            temperature: parseFloat(document.getElementById('step1-temperature').value),
            max_tokens: parseInt(document.getElementById('step1-max-tokens').value),
            system_prompt: _currentSystemPrompt,
        });
        status.innerHTML = '<span style="color:var(--success)">✓ Saved</span>';
        setTimeout(() => { status.innerHTML = ''; }, 2000);
        updatePromptPreview();
    } catch (e) {
        status.innerHTML = `<span style="color:var(--error)">✗ ${e.message}</span>`;
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save Parameters';
    }
}

async function runStep1() {
    const btn = document.getElementById('step1-run-btn');
    const status = document.getElementById('step1-run-status');
    const errorDiv = document.getElementById('step1-error');

    btn.disabled = true;
    btn.textContent = 'Running...';
    status.innerHTML = '<span class="spinner"></span> Calling Anthropic API...';
    errorDiv.style.display = 'none';

    try {
        await saveBriefAndCount();
        // Check if save failed (e.g. no project)
        const saved = await API.get('/api/step/1/data');
        if (!saved.topic || !saved.topic.trim()) {
            status.innerHTML = '<span style="color:var(--error)">✗ Failed</span>';
            showError('Could not save your brief. Do you have a project loaded? Go to Project and create one.');
            btn.disabled = false;
            btn.textContent = '🚀 Generate Subtopics';
            return;
        }
        const result = await API.post('/api/step/1/run', {});

        if (result.ok && result.subtopics) {
            status.innerHTML = '<span style="color:var(--success)">✓ Completed</span>';
            renderSubtopics(result.subtopics);
        } else {
            status.innerHTML = '<span style="color:var(--error)">✗ Failed</span>';
            showError(result.error || 'Unknown error');
        }
    } catch (e) {
        status.innerHTML = '<span style="color:var(--error)">✗ Failed</span>';
        showError(e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '🚀 Generate Subtopics';
    }
}

function renderSubtopics(subtopics) {
    const output = document.getElementById('step1-output');
    output.innerHTML = `
        <div id="subtopic-cards">
            ${subtopics.map(st => `
                <div class="subtopic-card" style="background:var(--surface2); border-radius:var(--radius); padding:16px; margin-bottom:14px; border-left:3px solid var(--accent);">
                    <div style="display:flex; align-items:baseline; gap:10px; margin-bottom:10px;">
                        <span style="font-weight:700; color:var(--accent); font-size:14px; flex-shrink:0;">#${st.id}</span>
                        <span style="font-weight:600; font-size:15px; line-height:1.4;">${escapeHtml(st.title || '(untitled)')}</span>
                    </div>
                    <div style="margin-bottom:8px;">
                        <span style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px;">Angle</span>
                        <p style="margin:2px 0 0 0; font-size:13px; line-height:1.5; color:var(--text);">${escapeHtml(st.angle || '—')}</p>
                    </div>
                    <div style="margin-bottom:8px;">
                        <span style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px;">Research Info</span>
                        <p style="margin:2px 0 0 0; font-size:13px; line-height:1.5; color:var(--text);">${escapeHtml(st.research_info || '—')}</p>
                    </div>
                    <div style="margin-bottom:0;">
                        <span style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px;">Search Query</span>
                        <p style="margin:2px 0 0 0; font-size:12px; font-family:var(--mono); color:var(--accent); background:var(--bg); padding:6px 10px; border-radius:4px; word-break:break-all;">${escapeHtml(st.search_query || '—')}</p>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function showError(message) {
    const errorDiv = document.getElementById('step1-error');
    errorDiv.style.display = 'block';
    errorDiv.innerHTML = `<div class="error-box">${escapeHtml(message)}</div>`;
}

function hideError() {
    const errorDiv = document.getElementById('step1-error');
    errorDiv.style.display = 'none';
    errorDiv.innerHTML = '';
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
