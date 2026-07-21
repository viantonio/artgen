// System log widget — renders in the bottom bar, hidden by default

const LogWidget = {
    entries: [],
    maxVisible: 4,
    visible: false,

    init() {
        this.container = document.getElementById('log-widget');
        this.toggleBtn = document.getElementById('toggle-log-btn');
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', () => this.toggle());
        }
        this.fetchLog();
        setInterval(() => this.fetchLog(), 5000);
    },

    toggle() {
        this.visible = !this.visible;
        if (this.visible) {
            this.container.classList.add('expanded');
            if (this.toggleBtn) this.toggleBtn.textContent = '▼ Hide';
            this.fetchLog();
        } else {
            this.container.classList.remove('expanded');
            if (this.toggleBtn) this.toggleBtn.textContent = '▶ Show';
        }
    },

    async fetchLog() {
        if (!this.visible) return;
        try {
            const data = await API.get('/api/log');
            this.entries = data.entries || [];
            this.render();
        } catch (e) {
            // Log endpoint not available yet — ignore
        }
    },

    render() {
        if (!this.container || !this.visible) return;
        const recent = this.entries.slice(-this.maxVisible);
        this.container.innerHTML = recent.map(e => {
            const ts = e.timestamp ? e.timestamp.split('T')[1].split('.')[0] : '';
            return `<div class="log-entry ${e.level}"><span class="ts">${ts}</span>${e.message}</div>`;
        }).join('');
        this.container.scrollTop = this.container.scrollHeight;
    }
};

document.addEventListener('DOMContentLoaded', () => {
    LogWidget.init();
});
