// Step 7: Final Assembly — backend-driven with local file output

let _articleText = '';
let _imageCards = [];

document.addEventListener('DOMContentLoaded', () => {
    initStep7();
});

async function initStep7() {
    await loadStep7Data();
    document.getElementById('step7-assemble-btn').addEventListener('click', assembleArticle);
}

async function loadStep7Data() {
    try {
        const step4 = await API.get('/api/step/4/data');
        const step6 = await API.get('/api/step/6/data');

        const step4Done = step4.status === 'completed' && step4.styled_article && step4.styled_article.trim();
        const step6Done = step6.status === 'completed' && step6.image_cards && step6.image_cards.length > 0;
        const step6Partial = step6.status === 'partial' && step6.image_cards && step6.image_cards.length > 0;

        const gatedCard = document.getElementById('step7-gated-card');
        const controlsCard = document.getElementById('step7-controls-card');
        const gatedStatus = document.getElementById('step7-gated-status');

        if (!step4Done) {
            gatedCard.style.display = 'block';
            controlsCard.style.display = 'none';
            gatedStatus.textContent = ' Step 4 (Style Rewrite) must be completed first.';
            return;
        }

        if (!step6Done && !step6Partial) {
            gatedCard.style.display = 'block';
            controlsCard.style.display = 'none';
            gatedStatus.textContent = ' Step 6 must have at least some images generated. Run Step 6 first.';
            return;
        }

        gatedCard.style.display = 'none';
        controlsCard.style.display = 'block';

        _articleText = step4.styled_article;
        _imageCards = step6.image_cards.filter(c => c.status === 'completed' && c.image_b64);

        document.getElementById('step7-assemble-btn').disabled = false;

        if (step6Partial) {
            const completed = _imageCards.length;
            const total = step6.image_cards.length;
            document.getElementById('step7-assemble-btn').textContent =
                `📄 Assemble & Save Article (${completed}/${total} images ready)`;
        }
    } catch (e) {
        console.error('Failed to load Step 7 data:', e);
        showError(e.message);
    }
}

async function assembleArticle() {
    const btn = document.getElementById('step7-assemble-btn');
    const outputCard = document.getElementById('step7-output-card');
    const output = document.getElementById('step7-output');
    const errorEl = document.getElementById('step7-error');

    btn.disabled = true;
    btn.textContent = '⏳ Assembling...';
    errorEl.style.display = 'none';

    try {
        const result = await API.post('/api/step/7/run', {});

        if (!result.ok) {
            showError(result.error);
            btn.disabled = false;
            btn.textContent = '📄 Assemble & Save Article';
            return;
        }

        // Build result display
        let resultHtml = `
            <div style="margin-bottom:16px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <span style="font-size:12px; color:var(--text-secondary);">
                    ${result.placed_count} image${result.placed_count !== 1 ? 's' : ''} inserted
                </span>
                <span style="font-size:12px; color:var(--success); font-weight:600;">✓ Assembled & Saved</span>
            </div>
        `;

        if (result.unplaced && result.unplaced.length > 0) {
            resultHtml += `
                <div class="error-box" style="margin-bottom:16px;">
                    ⚠ ${result.unplaced.length} image${result.unplaced.length !== 1 ? 's' : ''} could not be placed — anchor text not found in article.
                    Cards: ${result.unplaced.map(c => `#${c.id}`).join(', ')}
                </div>
            `;
        }

        // Download button
        resultHtml += `
            <div style="margin-bottom:16px;">
                <a href="${result.download_url}" class="btn" style="display:inline-block; text-decoration:none;">
                    💾 Download Article (HTML)
                </a>
                <span style="margin-left:8px; font-size:12px; color:var(--text-secondary);">
                    Self-contained file with embedded images — works offline
                </span>
            </div>
        `;

        // Rendered article preview
        resultHtml += `
            <div class="article-content" style="font-size:15px; line-height:1.8; color:var(--text);">
                ${result.html_content}
            </div>
        `;

        outputCard.style.display = 'block';
        output.innerHTML = resultHtml;
        btn.textContent = '📄 Assemble & Save Article';

    } catch (e) {
        console.error('Assembly failed:', e);
        showError(e.message);
        btn.disabled = false;
        btn.textContent = '📄 Assemble & Save Article';
    }
}

function showError(message) {
    const el = document.getElementById('step7-error');
    el.style.display = 'block';
    el.innerHTML = `<div class="error-box">${escapeHtml(message)}</div>`;
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
