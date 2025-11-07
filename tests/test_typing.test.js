// @ts-check
/// <reference types="jest" />

describe('Test Controller', () => {
    beforeEach(() => {
        // Set up DOM elements
        document.body.innerHTML = `
            <div id="paragraph-display"></div>
            <textarea id="typing-input" disabled></textarea>
            <div id="stress-display"></div>
            <button id="start-btn">Start Test</button>
            <button id="finish-btn" disabled>Finish Test</button>
            <button id="new-paragraph-btn" disabled>New Paragraph</button>
            <div id="wpm-display">0</div>
            <div id="accuracy-display">100%</div>
            <div id="time-display">0s</div>
            <video id="camera-feed"></video>
            <canvas id="capture-canvas"></canvas>
        `;
    });

    test('Start Test enables input and updates UI', async () => {
        // Mock fetch for paragraph
        globalThis.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ paragraph: 'Test paragraph' }),
            })
        );

        // Click start button
        const startBtn = /** @type {HTMLButtonElement | null} */ (document.getElementById('start-btn'));
        if (!startBtn) throw new Error('start button not found');
        startBtn.click();

        // Wait for async operations
        await new Promise(resolve => setTimeout(resolve, 100));

        // Check UI state
        const input = /** @type {HTMLTextAreaElement | null} */ (document.getElementById('typing-input'));
        if (!input) throw new Error('typing input not found');
        const paragraphDisplay = /** @type {HTMLElement | null} */ (document.getElementById('paragraph-display'));
        if (!paragraphDisplay) throw new Error('paragraph display not found');
        const finishBtn = /** @type {HTMLButtonElement | null} */ (document.getElementById('finish-btn'));
        if (!finishBtn) throw new Error('finish button not found');

        expect(input.disabled).toBeFalsy();
        expect(paragraphDisplay.textContent).toBe('Test paragraph');
        expect(startBtn.disabled).toBeTruthy();
        expect(finishBtn.disabled).toBeFalsy();
    });

    test('Progress tracking works correctly', async () => {
        // Mock Date.now
        const now = Date.now();
        jest.spyOn(Date, 'now').mockImplementation(() => now);

        // Start test
        await startTest();

        // Simulate typing
        const input = /** @type {HTMLTextAreaElement | null} */ (document.getElementById('typing-input'));
        if (!input) throw new Error('typing input not found');
        input.value = 'Test';
        input.dispatchEvent(new Event('input'));

        // Advance time by 1 second
        jest.spyOn(Date, 'now').mockImplementation(() => now + 1000);

        // Update stats
        statsController.update();

        // Check WPM calculation
        const wpmDisplay = /** @type {HTMLElement | null} */ (document.getElementById('wpm-display'));
        if (!wpmDisplay) throw new Error('wpm display not found');
        expect(wpmDisplay.textContent).toBe('60');

        // Restore mocked Date.now
        jest.restoreAllMocks();
    });

    test('Camera error handling', async () => {
        // Mock failed getUserMedia
        Object.defineProperty(globalThis, 'navigator', {
            value: { mediaDevices: { getUserMedia: () => Promise.reject(new Error('NotAllowedError')) } },
            configurable: true,
        });

        // Initialize webcam
        await webcamController.init();

        // Check error message
        const stressDisplay = /** @type {HTMLElement | null} */ (document.getElementById('stress-display'));
        if (!stressDisplay) throw new Error('stress display not found');
        expect(stressDisplay.textContent).toBe('Camera Permission Denied');
    });

    test('Finish test submits results', async () => {
        // Mock successful test completion
        globalThis.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ session_id: 'test_123' }),
            })
        );

        // Set up test state
        testController.data.testActive = true;
        // allow assignment despite original type by using any cast
        testController.data.startTime = /** @type {any} */ (Date.now() - 60000); // 1 minute ago

        const input = /** @type {HTMLTextAreaElement | null} */ (document.getElementById('typing-input'));
        if (!input) throw new Error('typing input not found');
        input.value = 'Test typing input';

        // Finish test
        await finishTest();

        // Verify API call
        expect(globalThis.fetch).toHaveBeenCalledWith('/submit_results', expect.any(Object));
        expect(window.location.href).toContain('/results/test_123');
    });
});