// Step 1: Outline UI

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
        updateModelSpecificParams();
        updatePromptPreview();
    });
    document.getElementById('step1-temperature').addEventListener('change', () => updatePromptPreview());
    document.getElementById('step1-max-tokens').addEventListener('change', () => updatePromptPreview());
    document.getElementById('step1-thinking-budget').addEventListener('change', () => updatePromptPreview());
    document.getElementById('step1-effort').addEventListener('change', () => updatePromptPreview());

    updatePromptPreview();
}

async function loadStep1Data() {
    try {
        const data = await API.get('/api/step/1/data');
        document.getElementById('step1-topic').value = data.brief || '';
        document.getElementById('step1-count').value = data.middle_count || 1;

        if (data.cards && data.cards.length > 0) {
            renderCards(data.cards);
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
        document.getElementById('step1-thinking-budget').value = params.thinking_budget || 1600;
        document.getElementById('step1-effort').value = params.effort || 'high';
        document.getElementById('step1-system-prompt').value = params.system_prompt || '';
        _currentSystemPrompt = params.system_prompt || '';
        updateModelSpecificParams();
    } catch (e) {
        console.error('Failed to load Step 1 params:', e);
    }
}

async function saveBriefAndCount() {
    const brief = document.getElementById('step1-topic').value;
    const middleCount = parseInt(document.getElementById('step1-count').value) || 1;
    try {
        const result = await API.put('/api/step/1/data', {
            brief: brief,
            middle_count: middleCount,
            cards: [],
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
    const middleCount = parseInt(document.getElementById('step1-count').value) || 1;
    const totalCards = middleCount + 2;
    const systemPrompt = _currentSystemPrompt || '(no system prompt set)';

    const schema = JSON.stringify({
        type: "object",
        properties: {
            cards: {
                type: "array",
                items: {
                    type: "object",
                    properties: {
                        id: { type: "integer", description: "1-based index" },
                        type: { type: "string", description: "Card type: 'beginning', 'middle', or 'end'" },
                        title: { type: "string", description: "Sharp, clickable section headline" },
                        angle: { type: "string", description: "The argument this card makes" },
                        ammo: { type: "string", description: "Braindump of raw material for the draft writer" }
                    },
                    required: ["id", "type", "title", "angle", "ammo"],
                    additionalProperties: false
                }
            }
        },
        required: ["cards"],
        additionalProperties: false
    }, null, 2);

    const userMessage = `BRIEF: ${brief}\n\nGenerate 1 beginning card, ${middleCount} middle cards, and 1 end card (${totalCards} cards total). Each card needs a type, title, angle, and ammo as specified in the output schema.\n\nRemember: the AMMO field is the most important output. It's a braindump of raw material for the draft writer — be generous, messy, and maximalist.\n\nReturn ONLY valid JSON.`;

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
            thinking_budget: parseInt(document.getElementById('step1-thinking-budget').value),
            effort: document.getElementById('step1-effort').value,
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

function updateModelSpecificParams() {
    const isHaiku = _currentModel.startsWith('claude-haiku');
    document.getElementById('step1-thinking-budget-group').style.display = isHaiku ? 'block' : 'none';
    document.getElementById('step1-effort-group').style.display = isHaiku ? 'none' : 'block';
    // Haiku requires temp = 1.0 for thinking
    if (isHaiku) {
        document.getElementById('step1-temperature').value = 1.0;
        document.getElementById('temp-value').textContent = '1.0';
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
        if (!saved.brief || !saved.brief.trim()) {
            status.innerHTML = '<span style="color:var(--error)">✗ Failed</span>';
            showError('Could not save your brief. Do you have a project loaded? Go to Project and create one.');
            btn.disabled = false;
            btn.textContent = '🚀 Generate Outline';
            return;
        }
        const result = await API.post('/api/step/1/run', {});

        if (result.ok && result.cards) {
            status.innerHTML = '<span style="color:var(--success)">✓ Completed</span>';
            renderCards(result.cards);
        } else {
            status.innerHTML = '<span style="color:var(--error)">✗ Failed</span>';
            showError(result.error || 'Unknown error');
        }
    } catch (e) {
        status.innerHTML = '<span style="color:var(--error)">✗ Failed</span>';
        showError(e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '🚀 Generate Outline';
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

function renderCards(cards) {
    const output = document.getElementById('step1-output');

    // Count middle cards for proper numbering
    let middleIdx = 0;
    const labels = cards.map(c => {
        if (c.type === 'beginning') return 'Beginning';
        if (c.type === 'end') return 'End';
        middleIdx++;
        return `Middle #${middleIdx}`;
    });

    output.innerHTML = `
        <div id="subtopic-cards">
            ${cards.map((card, i) => {
                const ammoText = card.ammo || '';
                const ammoTruncated = ammoText.length > 300;
                const previewText = ammoTruncated ? ammoText.substring(0, 300) + '...' : ammoText;

                return `
                <div class="subtopic-card" style="background:var(--surface2); border-radius:var(--radius); padding:16px; margin-bottom:14px; border-left:3px solid var(--accent);">
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px; flex-wrap:wrap;">
                        ${getTypeBadge(card.type)}
                        <span style="font-size:11px; color:var(--text-secondary);">${labels[i]}</span>
                        <span style="font-weight:600; font-size:15px; line-height:1.4; flex:1; min-width:200px;">${escapeHtml(card.title || '(untitled)')}</span>
                    </div>
                    <div style="margin-bottom:8px;">
                        <span style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px;">Angle</span>
                        <p style="margin:2px 0 0 0; font-size:13px; line-height:1.5; color:var(--text);">${escapeHtml(card.angle || '—')}</p>
                    </div>
                    <div style="margin-bottom:0;">
                        <span style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.5px;">Ammo ${ammoTruncated ? `<span style="color:var(--accent); cursor:pointer; font-size:11px;" onclick="this.closest('.subtopic-card').querySelector('.ammo-full').style.display='block'; this.closest('.subtopic-card').querySelector('.ammo-preview').style.display='none'; this.style.display='none';">(show all — ${ammoText.length} chars)</span>` : ''}</span>
                        <div class="ammo-preview" style="margin-top:4px; font-size:13px; line-height:1.5; color:var(--text); white-space:pre-wrap;">${escapeHtml(previewText)}</div>
                        ${ammoTruncated ? `<div class="ammo-full" style="display:none; margin-top:4px; font-size:13px; line-height:1.5; color:var(--text); white-space:pre-wrap;">${escapeHtml(ammoText)}</div>` : ''}
                    </div>
                </div>
                `;
            }).join('')}
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
