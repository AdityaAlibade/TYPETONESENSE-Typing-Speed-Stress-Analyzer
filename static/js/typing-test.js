// DOM cache to avoid repeated lookups
const DOM = {
    video: null,
    canvas: null,
    typingInput: null,
    paragraphDisplay: null,
    startBtn: null,
    finishBtn: null,
    newParagraphBtn: null,
    wpmDisplay: null,
    accuracyDisplay: null,
    timeDisplay: null,
    stressDisplay: null
};

// 🎥 Webcam Handling Controller
const webcamController = {
    stream: null,
    context: null,

    async init() {
        try {
            DOM.canvas = document.getElementById('capture-canvas');
            DOM.video = document.getElementById('camera-feed');
            DOM.stressDisplay = document.getElementById('stress-display');

            if (!navigator.mediaDevices?.getUserMedia) {
                throw new Error('WebRTC not supported in this browser.');
            }

            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
                audio: false
            });

            DOM.video.srcObject = this.stream;
            await DOM.video.play();

            // set canvas size from actual video settings (fallback to element size)
            const settings = this.stream.getVideoTracks()[0].getSettings();
            DOM.canvas.width = settings.width || DOM.video.videoWidth || 640;
            DOM.canvas.height = settings.height || DOM.video.videoHeight || 480;
            this.context = DOM.canvas.getContext('2d');

            return true;
        } catch (error) {
            console.error('❌ Webcam init error:', error);
            this.handleWebcamError(error);
            return false;
        }
    },

    handleWebcamError(error) {
        const messages = {
            NotFoundError: 'No Camera Detected',
            NotReadableError: 'Camera Already In Use',
            NotAllowedError: 'Camera Permission Denied',
            AbortError: 'Camera Access Aborted'
        };
        const message = messages[error?.name] || 'Camera Access Error';
        this.updateStressDisplay(message, 'error');
    },

    updateStressDisplay(level, type = 'status') {
        if (!DOM.stressDisplay) DOM.stressDisplay = document.getElementById('stress-display');
        const display = DOM.stressDisplay;
        if (!display) return;

        display.textContent = level;
        display.dataset.level = (level || '').toLowerCase();
        display.className = 'stress-level';
        display.style.color = type === 'error' ? 'crimson' : '';
    },

    async captureFrame() {
        if (!DOM.canvas || !this.context || !this.stream) {
            console.warn('⚠️ Missing webcam components');
            return null;
        }

        if (!DOM.video || DOM.video.readyState !== DOM.video.HAVE_ENOUGH_DATA) {
            // Not enough data yet
            return null;
        }

        try {
            this.context.drawImage(DOM.video, 0, 0, DOM.canvas.width, DOM.canvas.height);
            return await new Promise(resolve => DOM.canvas.toBlob(resolve, 'image/jpeg', 0.7));
        } catch (error) {
            console.error('Frame capture error:', error);
            return null;
        }
    },

    cleanup() {
        this.stream?.getTracks().forEach(track => track.stop());
        this.stream = null;
    }
};

// 🧠 Test Data & Flow Controller
const testController = {
    data: {
        startTime: null,
        originalText: '',
        testActive: false,
        keystrokes: 0,
        errors: 0,
        sessionId: null,
        progress: [],
        _lastProgressPush: 0
    },

    intervals: { update: null, stress: null },

    reset() {
        Object.assign(this.data, {
            startTime: null,
            originalText: '',
            testActive: false,
            keystrokes: 0,
            errors: 0,
            sessionId: null,
            progress: [],
            _lastProgressPush: 0
        });
    },

    cleanup() {
        this.data.testActive = false;
        Object.values(this.intervals).forEach(clearInterval);
        this.intervals = { update: null, stress: null };
    },

    async analyze() {
        if (!this.data.testActive) return;

        const blob = await webcamController.captureFrame();
        if (!blob) return;

        try {
            const fd = new FormData();
            fd.append('image', blob, 'frame.jpg');
            if (this.data.sessionId) fd.append('session_id', this.data.sessionId);

            const res = await fetch('/analyze_frame_blob', { method: 'POST', body: fd });
            if (!res.ok) throw new Error(`HTTP error: ${res.status}`);

            const result = await res.json();
            if (result?.stress_level) {
                webcamController.updateStressDisplay(result.stress_level);
            }
        } catch (error) {
            console.error('Analysis error:', error);
            webcamController.updateStressDisplay('Analysis Error', 'error');
        }
    }
};

// 🚫 Clipboard and Copy Restriction
const clipboardController = {
    handlers: {},

    enable() {
        const preventAction = e => {
            if (testController.data.testActive) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
        };

        const blockShortcuts = e => {
            if (!testController.data.testActive) return;
            const isCtrl = e.ctrlKey || e.metaKey;
            if (isCtrl && ['v', 'c', 'x', 'a'].includes(e.key?.toLowerCase())) {
                e.preventDefault();
            }
        };

        const input = document.getElementById('typing-input');
        const para = document.getElementById('paragraph-display');

        ['paste', 'copy', 'cut', 'drop', 'contextmenu'].forEach(ev => {
            input?.addEventListener(ev, preventAction);
            para?.addEventListener(ev, preventAction);
            document.addEventListener(ev, preventAction);
        });
        document.addEventListener('keydown', blockShortcuts);

        this.handlers = { preventAction, blockShortcuts };
    },

    disable() {
        const { preventAction, blockShortcuts } = this.handlers;
        if (!preventAction) return;

        const input = document.getElementById('typing-input');
        const para = document.getElementById('paragraph-display');

        ['paste', 'copy', 'cut', 'drop', 'contextmenu'].forEach(ev => {
            input?.removeEventListener(ev, preventAction);
            para?.removeEventListener(ev, preventAction);
            document.removeEventListener(ev, preventAction);
        });
        document.removeEventListener('keydown', blockShortcuts);

        this.handlers = {};
    }
};

// 📊 Stats Controller
const statsController = {
    elements: {},

    init() {
        this.elements = {
            wpm: document.getElementById('wpm-display'),
            accuracy: document.getElementById('accuracy-display'),
            time: document.getElementById('time-display'),
            input: document.getElementById('typing-input'),
            paragraph: document.getElementById('paragraph-display')
        };
    },

    update() {
        if (!testController.data.testActive || !testController.data.startTime) return;

        const now = Date.now();
        const elapsed = (now - testController.data.startTime) / 1000;
        const input = this.elements.input;
        if (!input) return;

        const text = input.value.trim();
        const words = text ? text.split(/\s+/).length : 0;
        const wpm = elapsed > 0 && words > 0 ? Math.round((words / elapsed) * 60) : 0;

        let correct = 0;
        const minLen = Math.min(input.value.length, testController.data.originalText.length);
        for (let i = 0; i < minLen; i++) {
            if (input.value[i] === testController.data.originalText[i]) correct++;
        }

        const accuracy = input.value.length ? Math.round((correct / input.value.length) * 100) : 100;

        this.elements.wpm.textContent = wpm;
        this.elements.accuracy.textContent = `${accuracy}%`;
        this.elements.time.textContent = `${Math.round(elapsed)}s`;

        // Throttle progress pushes to once per second to avoid huge arrays
        if (elapsed > 0 && wpm > 0) {
            const nowSec = Math.floor(elapsed);
            if (nowSec !== testController.data._lastProgressPush) {
                testController.data.progress.push(wpm);
                testController.data._lastProgressPush = nowSec;
            }
        }
    }
};

// ⚙️ Initialize Test Environment
async function initializeTest() {
    // Populate common DOM references
    DOM.typingInput = document.getElementById('typing-input');
    DOM.paragraphDisplay = document.getElementById('paragraph-display');
    DOM.startBtn = document.getElementById('start-btn');
    DOM.finishBtn = document.getElementById('finish-btn');
    DOM.newParagraphBtn = document.getElementById('new-paragraph-btn');
    DOM.wpmDisplay = document.getElementById('wpm-display');
    DOM.accuracyDisplay = document.getElementById('accuracy-display');
    DOM.timeDisplay = document.getElementById('time-display');

    statsController.init();
    const webcamReady = await webcamController.init();
    // Allow starting the test even if the webcam is unavailable.
    // The stress analysis will be skipped if no webcam/stream is present.
    if (!webcamReady) {
        console.warn('Webcam not ready — test can proceed without camera.');
        webcamController.updateStressDisplay('Camera Unavailable', 'error');
    }

    // Attach UI event handlers (avoid relying on inline onclick attributes so module scope works)
    if (DOM.startBtn) DOM.startBtn.addEventListener('click', startTest);
    if (DOM.finishBtn) DOM.finishBtn.addEventListener('click', finishTest);
    if (DOM.newParagraphBtn) DOM.newParagraphBtn.addEventListener('click', newParagraph);

    return webcamReady;
}

// ▶️ Start Test
async function startTest() {
    try {
        if (testController.data.testActive) return;

        // Show loading state
        if (DOM.startBtn) {
            DOM.startBtn.disabled = true;
            DOM.startBtn.innerHTML = '<span class="loading-spinner"></span>Loading...';
        }
        
        const res = await fetch('/get_paragraph');
        const data = await res.json();

        testController.reset();
        testController.data.originalText = data.paragraph;
        
        // Add test-starting animation to paragraph display
        if (DOM.paragraphDisplay) {
            DOM.paragraphDisplay.classList.add('test-starting');
            DOM.paragraphDisplay.textContent = data.paragraph;
            // Remove animation class after it completes
            setTimeout(() => {
                DOM.paragraphDisplay.classList.remove('test-starting');
            }, 500);

                if (DOM.typingInput) {
                    DOM.typingInput.disabled = false;
                    DOM.typingInput.value = '';
                    DOM.typingInput.focus();
                }
        }

    testController.data.sessionId = `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
    testController.data.startTime = Date.now();
    testController.data.testActive = true;

        clipboardController.enable();

    if (DOM.startBtn) DOM.startBtn.disabled = true;
    if (DOM.finishBtn) DOM.finishBtn.disabled = false;
    if (DOM.newParagraphBtn) DOM.newParagraphBtn.disabled = false;

    testController.intervals.update = setInterval(() => statsController.update(), 250);
    testController.intervals.stress = setInterval(() => testController.analyze(), 2000);
    } catch (error) {
        console.error('❌ Start test error:', error);
        alert('Error starting test. Please try again.');
    }
}

// ⏹ Finish Test
async function finishTest() {
    if (!testController.data.testActive) return;

    testController.cleanup();
    clipboardController.disable();

    try {
    const input = DOM.typingInput || document.getElementById('typing-input');
    const elapsed = (Date.now() - testController.data.startTime) / 1000;
    const text = input?.value?.trim() || '';
    const words = text ? text.split(/\s+/).length : 0;
    const wpm = elapsed > 0 && words > 0 ? Math.round((words / elapsed) * 60) : 0;

                let correct = 0;
                const minLen = Math.min((input?.value?.length || 0), testController.data.originalText.length);
                for (let i = 0; i < minLen; i++) {
                    if (input.value[i] === testController.data.originalText[i]) correct++;
                }

                const accuracy = (input && input.value.length) ? Math.round((correct / input.value.length) * 100) : 100;

        const res = await fetch('/submit_results', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                wpm, accuracy,
                typing_time: elapsed,
                session_id: testController.data.sessionId,
                progress: testController.data.progress
            })
        });

        const result = await res.json();
        if (result.session_id) {
            window.location.href = `/results/${result.session_id}`;
        } else {
            throw new Error('Missing session ID in response.');
        }
    } catch (error) {
        console.error('❌ Submit results error:', error);
        alert('Error submitting results. Please try again.');
    }
}

// 🔁 Start a New Paragraph/Test
async function newParagraph() {
    if (testController.data.testActive && !confirm('Start a new test? Previous data will be lost.')) return;

        testController.cleanup();
        clipboardController.disable();

        if (DOM.startBtn) DOM.startBtn.disabled = false;
        if (DOM.finishBtn) DOM.finishBtn.disabled = true;
        if (DOM.newParagraphBtn) DOM.newParagraphBtn.disabled = true;

        if (DOM.typingInput) {
            DOM.typingInput.disabled = true;
            DOM.typingInput.value = '';
        }

        statsController.init();
        startTest();
}

// 🌐 Event Listeners
window.addEventListener('DOMContentLoaded', initializeTest);
window.addEventListener('beforeunload', () => {
    testController.cleanup();
    clipboardController.disable();
    webcamController.cleanup();
});
