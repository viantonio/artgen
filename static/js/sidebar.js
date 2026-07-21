// Shared sidebar logic — loads project info, status dots, and gates step access

document.addEventListener('DOMContentLoaded', () => {
    loadSidebarProjectInfo();
});

async function loadSidebarProjectInfo() {
    try {
        const project = await API.get('/api/project');
        const nameEl = document.getElementById('sidebar-project-name');
        const hasProject = project && project.name;

        if (nameEl && hasProject) {
            nameEl.textContent = project.name;
        } else if (nameEl && !hasProject) {
            nameEl.textContent = 'No project';
        }

        if (project.steps) {
            for (let i = 1; i <= 5; i++) {
                const dot = document.getElementById(`dot-step${i}`);
                if (dot && project.steps[i]) {
                    dot.className = 'step-dot ' + (project.steps[i].status || 'idle');
                }
            }
        }

        // Access gating: step pages require a project to be loaded
        const path = window.location.pathname;
        const isStepPage = /^\/step\/\d+/.test(path);

        if (isStepPage && !hasProject) {
            // Redirect to project page — no project loaded
            window.location.replace('/');
            return;
        }

        // Visually gate sidebar step links
        document.querySelectorAll('.step-link').forEach(link => {
            if (!hasProject) {
                link.classList.add('gated');
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    window.location.replace('/');
                });
            }
        });
    } catch (e) {
        console.error('Failed to load sidebar project info:', e);
    }
}
