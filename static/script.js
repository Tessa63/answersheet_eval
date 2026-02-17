document.addEventListener('DOMContentLoaded', () => {

    // Helper to setup file input interactions
    function setupFileInput(inputId, nameId, zoneId) {
        const input = document.getElementById(inputId);
        const nameDisplay = document.getElementById(nameId);
        const zone = document.getElementById(zoneId);

        // Update name on change
        input.addEventListener('change', (e) => {
            if (input.files && input.files.length > 0) {
                nameDisplay.textContent = input.files[0].name;
                zone.style.borderColor = 'var(--primary-color)';
                zone.style.backgroundColor = '#eef2ff';
            } else {
                nameDisplay.textContent = '';
                zone.style.borderColor = '';
                zone.style.backgroundColor = '';
            }
        });

        // Drag and drop visuals
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            zone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            zone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            zone.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            zone.classList.add('dragover');
        }

        function unhighlight(e) {
            zone.classList.remove('dragover');
        }
    }

    setupFileInput('student_file', 'name-student', 'zone-student');
    setupFileInput('model_file', 'name-model', 'zone-model');
    setupFileInput('question_file', 'name-question', 'zone-question');

    // Loading State with AJAX submission
    const form = document.getElementById('upload-form');
    const overlay = document.getElementById('loading-overlay');
    const loadingTitle = document.getElementById('loading-title');
    const loadingText = document.getElementById('loading-status-text');

    form.addEventListener('submit', (e) => {
        e.preventDefault();

        const sFile = document.getElementById('student_file').files;
        const mFile = document.getElementById('model_file').files;

        if (sFile.length === 0 || mFile.length === 0) {
            alert('Please upload both Student Answer and Model Answer files.');
            return;
        }

        // Show loading overlay
        overlay.style.display = 'flex';
        if (loadingTitle) loadingTitle.textContent = 'Analyzing Content...';
        if (loadingText) loadingText.textContent = 'Uploading files...';

        const formData = new FormData(form);
        const startTime = Date.now();

        // 1. Submit files -- server returns 202 immediately
        fetch('/evaluate', {
            method: 'POST',
            body: formData
        })
            .then(response => {
                if (!response.ok && response.status !== 202) {
                    return response.json().then(data => {
                        throw new Error(data.error || `Server error (${response.status})`);
                    }).catch(e => {
                        if (e.message) throw e;
                        throw new Error(`Server error (${response.status})`);
                    });
                }
                // Files accepted -- start polling for progress
                startPolling(startTime);
            })
            .catch(error => {
                overlay.style.display = 'none';
                const errorMsg = error.message || 'An unknown error occurred.';
                alert('Upload Failed:\n\n' + errorMsg + '\n\nPlease check your files and try again.');
                console.error('Upload error:', error);
            });
    });

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
                        // Navigate to results page
                        window.location.href = '/results';
                    } else if (data.status === 'error') {
                        clearInterval(pollInterval);
                        overlay.style.display = 'none';
                        alert('Evaluation Failed:\n\n' + (data.message || 'Unknown error') + '\n\nPlease check your files and try again.');
                    }
                })
                .catch(() => {
                    // Ignore polling errors silently
                });
        }, 2000);
    }
});
