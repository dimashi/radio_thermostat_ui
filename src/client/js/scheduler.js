function scheduler() {
    return {
        days: {},
        originalDays: {},
        state: null,
        showOtherFields: false,
        scheduleLoaded: false,
        stateLoaded: false,
        // Defaults (kept simple; schedule will be populated from server)
        defaultSlot: { time: '00:00', temp: '0' },
        defaultSlots: [ { time: '00:00', temp: '0' }, { time: '00:00', temp: '0' }, { time: '00:00', temp: '0' }, { time: '00:00', temp: '0' } ],
        defaultDays: { 'Mon': [], 'Tue': [], 'Wed': [], 'Thu': [], 'Fri': [], 'Sat': [], 'Sun': [] },
        async init() {
            const schedulePromise = this.loadSchedule();
            await this.loadState();
            await schedulePromise;
        },
        async loadSchedule() {
            try {
                const response = await fetch('/api/schedule');
                if (response.ok) {
                    this.days = await response.json();
                    this.originalDays = JSON.parse(JSON.stringify(this.days));
                } else { this.days = {}; }
            } catch (error) { console.error('Error loading schedule:', error); this.days = {}; }
            finally { this.scheduleLoaded = true; }
        },
        async loadState() {
            try {
                const response = await fetch('/api/state');
                if (response.ok) { this.state = await response.json(); } 
                else { this.state = null; }
            } catch (error) { console.error('Error loading state:', error); this.state = null; }
            finally { this.stateLoaded = true; }
        },
        getOriginalValue(day, index, field) {
            let value = this.originalDays[day]?.[index]?.[field] || '';
            if (value && field === 'time') {
                try {
                    value = Temporal.PlainTime.from(value).toLocaleString();
                } catch (e) {
                    // Fallback: return as-is if Temporal not available or parse fails
                }
            }
            return value; 
        },
        hasChanged(day, index, field) { return this.days[day]?.[index]?.[field] != this.originalDays[day]?.[index]?.[field]; },
        getThermostatToServerTimeDiff() {
            if (!this.state?.time || !this.state?.server_time) return '';
            const thermostatMinutes = this.state.time.hour * 60 + this.state.time.minute;
            const serverMinutes = this.state.server_time.hour * 60 + this.state.server_time.minute;
            let diff = Math.abs(thermostatMinutes - serverMinutes);
            if (diff > 12 * 60) diff = 24 * 60 - diff;
            return diff;
        },
        getTimeDiffClass() {
            const diff = this.getThermostatToServerTimeDiff();
            if (diff < 1) return 'time-sync-green';
            if (diff < 15) return 'time-sync-yellow';
            return 'time-sync-red';
        },
        async submitSchedule() {
            const response = await fetch('/api/schedule', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.days)
            });
            if (response.ok) {
                this.originalDays = JSON.parse(JSON.stringify(this.days));
                alert('Schedule saved!');
            } else { alert('Error: ' + response.statusText); }
        }
    };
}

// Ensure the function is available on the global scope and log load for debugging
try {
    window.scheduler = scheduler;
    console.debug('[scheduler] loaded, type=', typeof window.scheduler);
} catch (e) {
    // In environments without window (unlikely in browser), skip
}
