// Step 7: Final Assembly — pure frontend, no API calls

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
                `📄 Assemble Article (${completed}/${total} images ready)`;
        }
    } catch (e) {
        console.error('Failed to load Step 7 data:', e);
        showError(e.message);
    }
}

function fuzzyFindAnchor(article, anchor) {
    // 1. Exact match
    let idx = article.indexOf(anchor);
    if (idx >= 0) return idx;

    // 2. Normalized match — collapse whitespace, strip markdown formatting
    const norm = (s) => s.replace(/[*_~`]/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
    const normArticle = norm(article);
    const normAnchor = norm(anchor);
    idx = normArticle.indexOf(normAnchor);
    if (idx >= 0) {
        // Map back to approximate position in original text
        return article.toLowerCase().indexOf(normAnchor.substring(0, 40));
    }

    // 3. Try with first 60 chars of anchor
    const shortAnchor = normAnchor.substring(0, 60);
    idx = normArticle.indexOf(shortAnchor);
    if (idx >= 0) {
        return article.toLowerCase().indexOf(shortAnchor.substring(0, 30));
    }

    // 4. Word-by-word — find where first 4 words appear
    const firstWords = normAnchor.split(/\s+/).slice(0, 4).join(' ');
    if (firstWords.length > 10) {
        idx = normArticle.indexOf(firstWords);
        if (idx >= 0) {
            return article.toLowerCase().indexOf(firstWords.substring(0, 20));
        }
    }

    return -1;
}

function assembleArticle() {
    if (!_articleText) {
        showError('No article text available.');
        return;
    }

    if (_imageCards.length === 0) {
        showError('No generated images available. Run Step 6 first.');
        return;
    }

    const outputCard = document.getElementById('step7-output-card');
    const output = document.getElementById('step7-output');

    // Position each card using fuzzy matching, get {card, startIdx, endIdx}
    const positioned = [];
    const notFound = [];

    for (const card of _imageCards) {
        const anchor = card.anchor_text || '';
        const startIdx = fuzzyFindAnchor(_articleText, anchor);
        if (startIdx < 0) {
            notFound.push(card);
        } else {
            // Use actual text from article at that position to determine end
            positioned.push({ card, startIdx });
        }
    }

    // Sort by position
    positioned.sort((a, b) => a.startIdx - b.startIdx);

    // Build assembled article by slicing at anchor points
    let html = '';
    let cursor = 0;

    for (const { card, startIdx } of positioned) {
        const anchor = card.anchor_text || '';

        // Text up to and including the anchor
        html += escapeHtml(_articleText.substring(cursor, startIdx + anchor.length));
        cursor = startIdx + anchor.length;

        // Insert image + caption
        html += `\n\n<figure style="margin:24px 0; text-align:center;">`;
        html += `<img src="data:image/png;base64,${card.image_b64}" style="max-width:100%; border-radius:8px;" alt="${escapeHtml(card.caption || '')}" />`;
        html += `<figcaption style="margin-top:8px; font-size:14px; font-style:italic; color:#888;">${escapeHtml(card.caption || '')}</figcaption>`;
        html += `</figure>\n\n`;
    }

    // Remaining text
    html += escapeHtml(_articleText.substring(cursor));

    // Light markdown rendering
    html = html
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/(?<!\*)\*([^*\n]+?)\*(?!\*)/g, '<em>$1</em>')
        .replace(/^## (.+)$/gm, '<h2 style="margin-top:24px;">$1</h2>')
        .replace(/^---$/gm, '<hr style="margin:24px 0; border:none; border-top:1px solid var(--border);" />');

    let resultHtml = `
        <div style="margin-bottom:16px; display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:12px; color:var(--text-secondary);">${positioned.length} image${positioned.length !== 1 ? 's' : ''} inserted</span>
            <span style="font-size:12px; color:var(--success); font-weight:600;">✓ Assembled</span>
        </div>
    `;

    if (notFound.length > 0) {
        resultHtml += `
            <div class="error-box" style="margin-bottom:16px;">
                ⚠ ${notFound.length} image${notFound.length !== 1 ? 's' : ''} could not be placed — anchor text not found in article.
                Cards: ${notFound.map(c => `#${c.id}`).join(', ')}
            </div>
        `;
    }

    resultHtml += `
        <div class="article-content" style="font-size:15px; line-height:1.8; color:var(--text);">
            ${html}
        </div>
    `;

    outputCard.style.display = 'block';
    output.innerHTML = resultHtml;
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
