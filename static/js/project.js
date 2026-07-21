// Project management — create, list, load, delete

document.addEventListener('DOMContentLoaded', async () => {
    await loadCurrentProject();
    await loadProjectList();
    setupButtons();
});

async function loadCurrentProject() {
    try {
        const project = await API.get('/api/project');
        const card = document.getElementById('current-project-card');
        const info = document.getElementById('current-project-info');

        if (project.exists && info) {
            card.style.display = 'block';
            const steps = project.steps || {};
            const stepStatuses = Object.entries(steps)
                .map(([n, s]) => `Step ${n}: <span class="status ${s.status}">${s.status}</span>`)
                .join(' &nbsp;|&nbsp; ');

            info.innerHTML = `
                <p><strong>${escapeHtml(project.name)}</strong></p>
                <p style="font-size:12px; color:var(--text-secondary);">Created: ${project.created ? project.created.split('T')[0] : 'N/A'}</p>
                <p style="margin-top:8px; font-size:13px;">${stepStatuses || 'No steps run yet'}</p>
            `;
        } else {
            card.style.display = 'none';
        }
    } catch (e) {
        console.error('Failed to load project:', e);
    }
}

async function loadProjectList() {
    try {
        const data = await API.get('/api/projects');
        const projects = data.projects || [];
        const currentDir = data.current;
        const listEl = document.getElementById('project-list');

        if (projects.length === 0) {
            listEl.innerHTML = '<p style="color:var(--text-secondary);">No projects yet. Create one above.</p>';
            return;
        }

        listEl.innerHTML = projects.map(p => {
            const isCurrent = p.dir_name === currentDir;
            const created = p.created ? p.created.split('T')[0] : '?';
            const rowStyle = isCurrent
                ? 'border-left:3px solid var(--accent); padding-left:12px;'
                : 'border-left:3px solid transparent; padding-left:12px;';

            return `
                <div style="display:flex; align-items:center; justify-content:space-between; padding:10px 0; border-bottom:1px solid var(--surface2); ${rowStyle}">
                    <div>
                        <strong>${escapeHtml(p.name)}</strong>
                        ${isCurrent ? '<span style="color:var(--accent); font-size:11px; margin-left:6px;">(active)</span>' : ''}
                        <span style="font-size:11px; color:var(--text-secondary); margin-left:8px;">${created}</span>
                    </div>
                    <div style="display:flex; gap:6px; flex-shrink:0;">
                        ${!isCurrent ? `<button class="secondary load-btn" data-dir="${escapeHtml(p.dir_name)}" style="font-size:12px; padding:4px 10px;">Load</button>` : ''}
                        <button class="secondary delete-btn" data-dir="${escapeHtml(p.dir_name)}" style="font-size:12px; padding:4px 10px; color:var(--error); border-color:var(--error);">🗑</button>
                    </div>
                </div>`;
        }).join('');

        // Wire up load buttons
        listEl.querySelectorAll('.load-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const dir = btn.dataset.dir;
                btn.disabled = true;
                btn.textContent = 'Loading...';
                try {
                    const result = await API.post(`/api/project/load/${encodeURIComponent(dir)}`, {});
                    if (result.ok) {
                        await loadCurrentProject();
                        await loadProjectList();
                    }
                } catch (e) {
                    alert('Failed to load: ' + e.message);
                    btn.disabled = false;
                    btn.textContent = 'Load';
                }
            });
        });

        // Wire up delete buttons
        listEl.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const dir = btn.dataset.dir;
                if (!confirm(`Delete project "${dir}"?\n\nThis will permanently delete all step data and cannot be undone.`)) {
                    return;
                }
                btn.disabled = true;
                btn.textContent = '...';
                try {
                    const result = await API.del(`/api/project/${encodeURIComponent(dir)}`);
                    if (result.ok) {
                        await loadCurrentProject();
                        await loadProjectList();
                    } else {
                        alert('Failed to delete: ' + result.error);
                        btn.disabled = false;
                        btn.textContent = '🗑';
                    }
                } catch (e) {
                    alert('Failed to delete: ' + e.message);
                    btn.disabled = false;
                    btn.textContent = '🗑';
                }
            });
        });
    } catch (e) {
        console.error('Failed to load project list:', e);
    }
}

function setupButtons() {
    const createBtn = document.getElementById('create-project-btn');
    const saveBtn = document.getElementById('save-project-btn');

    if (createBtn) {
        createBtn.addEventListener('click', async () => {
            const nameInput = document.getElementById('project-name');
            const name = nameInput.value.trim();
            const status = document.getElementById('create-status');

            createBtn.disabled = true;
            createBtn.textContent = 'Creating...';

            try {
                const result = await API.post('/api/project/new', { name });
                if (result.ok) {
                    status.innerHTML = `<span style="color:var(--success);">✓ Created "${result.name}" — go to Step 1 to begin</span>`;
                    nameInput.value = '';
                    await loadCurrentProject();
                    await loadProjectList();
                } else {
                    status.innerHTML = `<span style="color:var(--error);">✗ ${result.error}</span>`;
                }
            } catch (e) {
                status.innerHTML = `<span style="color:var(--error);">✗ ${e.message}</span>`;
            } finally {
                createBtn.disabled = false;
                createBtn.textContent = 'Create Project';
            }
        });
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';
            try {
                await API.post('/api/project/save', {});
                const status = document.getElementById('save-status');
                status.innerHTML = '<span style="color:var(--success); margin-left:12px;">✓ Saved</span>';
                setTimeout(() => { status.innerHTML = ''; }, 2000);
            } catch (e) {
                const status = document.getElementById('save-status');
                status.innerHTML = `<span style="color:var(--error); margin-left:12px;">✗ ${e.message}</span>`;
            } finally {
                saveBtn.disabled = false;
                saveBtn.textContent = '💾 Save';
            }
        });
    }
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
