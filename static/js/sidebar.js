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
        // Step N requires Step N-1 to be completed (sequential pipeline)
        const path = window.location.pathname;
        const isStepPage = /^\/step\/(\d+)/.test(path);
        const currentStepNum = isStepPage ? parseInt(path.match(/^\/step\/(\d+)/)[1]) : null;

        if (isStepPage && !hasProject) {
            window.location.replace('/');
            return;
        }

        // Visually gate sidebar step links — project required + sequential gating
        document.querySelectorAll('.step-link').forEach(link => {
            const hrefMatch = link.getAttribute('href').match(/^\/step\/(\d+)/);
            if (!hrefMatch) return;
            const stepNum = parseInt(hrefMatch[1]);

            let gated = false;
            let redirectTo = '/';

            if (!hasProject) {
                gated = true;
            } else if (stepNum > 1 && project.steps) {
                // Check if the previous step is completed
                const prevStatus = project.steps[stepNum - 1]?.status;
                if (prevStatus !== 'completed') {
                    gated = true;
                    redirectTo = `/step/${stepNum - 1}`;
                }
            }

            if (gated) {
                link.classList.add('gated');
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    window.location.replace(redirectTo);
                });
            }

            // If user is on a gated step page, redirect to the prerequisite
            if (currentStepNum === stepNum && gated) {
                window.location.replace(redirectTo);
            }
        });
    } catch (e) {
        console.error('Failed to load sidebar project info:', e);
    }
}
