document.addEventListener('DOMContentLoaded', () => {

    // ═══════════════════════════════════════════════
    //  File Input Setup (drag-drop, label, selected state)
    // ═══════════════════════════════════════════════
    function setupFileInput(inputId, nameId, zoneId) {
        const input = document.getElementById(inputId);
        const nameDisplay = document.getElementById(nameId);
        const zone = document.getElementById(zoneId);
        if (!input || !zone) return;

        input.addEventListener('change', () => {
            if (input.files && input.files.length > 0) {
                nameDisplay.textContent = '✓ ' + input.files[0].name;
                zone.classList.add('file-selected');
            } else {
                nameDisplay.textContent = '';
                zone.classList.remove('file-selected');
            }
        });

        // Drag & drop visuals
        const prevent = (e) => { e.preventDefault(); e.stopPropagation(); };
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(ev =>
            zone.addEventListener(ev, prevent, false)
        );
        ['dragenter', 'dragover'].forEach(ev =>
            zone.addEventListener(ev, () => zone.classList.add('dragover'), false)
        );
        ['dragleave', 'drop'].forEach(ev =>
            zone.addEventListener(ev, () => zone.classList.remove('dragover'), false)
        );
    }

    setupFileInput('student_file', 'name-student', 'zone-student');
    setupFileInput('model_file', 'name-model', 'zone-model');
    setupFileInput('question_file', 'name-question', 'zone-question');

    // ═══════════════════════════════════════════════
    //  Button Ripple Effect
    // ═══════════════════════════════════════════════
    const btn = document.getElementById('btn-evaluate');
    if (btn) {
        btn.addEventListener('click', function (e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            ripple.style.cssText = `
                position:absolute; border-radius:50%; pointer-events:none;
                width:${size}px; height:${size}px;
                left:${e.clientX - rect.left - size / 2}px;
                top:${e.clientY - rect.top - size / 2}px;
                background:rgba(255,255,255,.18);
                transform:scale(0); animation:ripple .6s ease forwards;
            `;
            this.appendChild(ripple);
            setTimeout(() => ripple.remove(), 700);
        });

        // Inject ripple keyframes once
        const style = document.createElement('style');
        style.textContent = `@keyframes ripple{to{transform:scale(2.5);opacity:0;}}`;
        document.head.appendChild(style);
    }

    // ═══════════════════════════════════════════════
    //  Form Submission with AJAX + Polling
    // ═══════════════════════════════════════════════
    const form = document.getElementById('upload-form');
    const overlay = document.getElementById('loading-overlay');
    const loadingTitle = document.getElementById('loading-title');
    const loadingText = document.getElementById('loading-status-text');

    if (form) {
        form.addEventListener('submit', (e) => {
            e.preventDefault();

            const sFile = document.getElementById('student_file').files;
            const mFile = document.getElementById('model_file').files;

            if (sFile.length === 0 || mFile.length === 0) {
                alert('Please upload both Student Answer and Model Answer files.');
                return;
            }

            // Show loading overlay
            if (overlay) overlay.style.display = 'flex';
            if (loadingTitle) loadingTitle.textContent = 'Analyzing Content...';
            if (loadingText) loadingText.textContent = 'Uploading files...';

            const formData = new FormData(form);
            const startTime = Date.now();

            fetch('/evaluate', {
                method: 'POST',
                body: formData
            })
                .then(response => {
                    if (!response.ok && response.status !== 202) {
                        return response.json().then(data => {
                            throw new Error(data.error || `Server error (${response.status})`);
                        }).catch(ex => {
                            if (ex.message) throw ex;
                            throw new Error(`Server error (${response.status})`);
                        });
                    }
                    startPolling(startTime);
                })
                .catch(error => {
                    if (overlay) overlay.style.display = 'none';
                    const msg = error.message || 'An unknown error occurred.';
                    alert('Upload Failed:\n\n' + msg + '\n\nPlease check your files and try again.');
                    console.error('Upload error:', error);
                });
        });
    }

    function startPolling(startTime) {
        const pollInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const mins = Math.floor(elapsed / 60);
            const secs = elapsed % 60;
            const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;

            fetch('/progress')
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'processing' && loadingText) {
                        loadingText.textContent = `Step ${data.step}/${data.total_steps}: ${data.message} (${timeStr})`;
                    } else if (data.status === 'done') {
                        clearInterval(pollInterval);
                        if (loadingTitle) loadingTitle.textContent = 'Almost done...';
                        if (loadingText) loadingText.textContent = 'Loading results...';
                        window.location.href = '/results';
                    } else if (data.status === 'error') {
                        clearInterval(pollInterval);
                        if (overlay) overlay.style.display = 'none';
                        alert('Evaluation Failed:\n\n' + (data.message || 'Unknown error') + '\n\nPlease check your files and try again.');
                    }
                })
                .catch(() => { /* ignore polling errors */ });
        }, 2000);
    }
});
