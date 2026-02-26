class TimeScheduler extends HTMLElement {
    async connectedCallback() {
        // Path configuration - adjust this to match your Python static route
        const basePath = '/components/time-scheduler';
        
        // 1. Inject Scoped CSS (Only once)
        if (!document.getElementById('ts-styles')) {
            const link = document.createElement('link');
            link.id = 'ts-styles';
            link.rel = 'stylesheet';
            link.href = `${basePath}/scheduler.css`;
            document.head.appendChild(link);
        }

        // 2. Fetch and Inject HTML Template
        const response = await fetch(`${basePath}/scheduler.html`);
        const templateHtml = await response.text();
        
        // Configuration from attributes
        const panels = JSON.parse(this.getAttribute('panels') || '[]');
        const storageKey = this.getAttribute('storage-key') || 'ts-default';
        const apiUrl = this.getAttribute('api-url');

        // Set the content
        this.innerHTML = templateHtml;

        // 3. Initialize Alpine Data for this instance
        // We use window.Alpine.nextTick to ensure the DOM is ready for Split.js
        window.Alpine.nextTick(() => {
            const alpineObj = Alpine.$data(this.querySelector('[x-data]'));
            if (alpineObj) {
                alpineObj.setup(panels, storageKey, apiUrl);
            }
        });
    }
}

// Register the component
customElements.define('time-scheduler', TimeScheduler);

// Define the Alpine Component Logic
document.addEventListener('alpine:init', () => {
    Alpine.data('timeSplitter', () => ({
        panels: [],
        storageKey: '',
        apiUrl: '',
        split: null,
        inputWidth: '8ch',

        setup(initialPanels, storageKey, apiUrl) {
            this.storageKey = storageKey;
            this.apiUrl = apiUrl;
            
            // Handle persistence manually to allow API overrides
            const saved = localStorage.getItem(`_x_${storageKey}`);
            this.panels = saved ? JSON.parse(saved) : initialPanels;

            this.detectLocaleWidth();
            this.initSplit();
        },

        initSplit() {
            this.$nextTick(() => {
                const ids = this.panels.map((_, i) => `#${this.getPanelId(i)}`);
                this.split = Split(ids, {
                    sizes: this.panels.map(p => p.size),
                    direction: 'vertical',
                    gutterSize: 10,
                    onDrag: (newSizes) => {
                        newSizes.forEach((s, i) => this.panels[i].size = s);
                        localStorage.setItem(`_x_${this.storageKey}`, JSON.stringify(this.panels));
                    }
                });
            });
        },

        getPanelId(index) { 
            return `p-${this.storageKey}-${index}`; 
        },

        detectLocaleWidth() {
            const isAmPm = /[a-z]/i.test(new Date().toLocaleTimeString());
            this.inputWidth = isAmPm ? '13ch' : '8ch';
        },

        formatTime(decimalHours) {
            let h = Math.floor(decimalHours), m = Math.round((decimalHours - h) * 60);
            if (m === 60) { h++; m = 0; }
            return `${String(h % 24).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
        },

        parseTime(timeStr) {
            const [h, m] = timeStr.split(':').map(Number);
            return h + (m / 60);
        },

        getGutterTime(index) {
            let sum = 0;
            for(let i = 0; i <= index; i++) sum += this.panels[i].size;
            return this.formatTime(sum * 0.24);
        },

        moveGutter(index, val) {
            let target = this.parseTime(val) / 0.24, prev = 0;
            for(let i = 0; i < index; i++) prev += this.panels[i].size;
            let next = (index + 2 < this.panels.length) ? (prev + this.panels[index].size + this.panels[index+1].size) : 100;
            
            target = Math.min(Math.max(prev, target), next);
            this.panels[index].size = target - prev;
            this.panels[index + 1].size = next - target;
            this.split.setSizes(this.panels.map(p => p.size));
            localStorage.setItem(`_x_${this.storageKey}`, JSON.stringify(this.panels));
        }
    }));
});