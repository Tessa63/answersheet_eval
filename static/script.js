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

    // Loading State with AJAX submission for proper error handling
    const form = document.getElementById('upload-form');
    const overlay = document.getElementById('loading-overlay');
    const loadingTitle = document.getElementById('loading-title');
    const loadingText = document.getElementById('loading-status-text');

    form.addEventListener('submit', (e) => {
        e.preventDefault(); // Prevent default form submission

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

        // Build FormData from the form
        const formData = new FormData(form);

        // --- Poll /progress for real-time status updates ---
        let pollInterval = setInterval(() => {
            fetch('/progress')
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'processing' && loadingText) {
                        loadingText.textContent = `Step ${data.step}/${data.total_steps}: ${data.message}`;
                    } else if (data.status === 'done' && loadingTitle) {
                        loadingTitle.textContent = 'Almost done...';
                        loadingText.textContent = 'Preparing results...';
                    }
                })
                .catch(() => {
                    // Ignore polling errors silently
                });
        }, 1500);

        // Submit via fetch for proper error handling
        fetch('/evaluate', {
            method: 'POST',
            body: formData
        })
            .then(response => {
                clearInterval(pollInterval); // Stop polling

                if (!response.ok) {
                    // Server returned an error (400, 500, etc.)
                    return response.text().then(errText => {
                        throw new Error(errText || `Server error (${response.status})`);
                    });
                }
                return response.text();
            })
            .then(html => {
                // Successfully got the result page — replace the document
                document.open();
                document.write(html);
                document.close();
            })
            .catch(error => {
                clearInterval(pollInterval); // Stop polling on error too

                // Hide the loading overlay
                overlay.style.display = 'none';

                // Show a user-friendly error
                const errorMsg = error.message || 'An unknown error occurred.';
                alert('Evaluation Failed:\n\n' + errorMsg + '\n\nPlease check your files and try again.');
                console.error('Evaluate error:', error);
            });
    });
});
