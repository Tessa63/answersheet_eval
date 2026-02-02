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

    // Loading State
    const form = document.getElementById('upload-form');
    const overlay = document.getElementById('loading-overlay');

    form.addEventListener('submit', (e) => {
        // Simple validation check visually (HTML5 'required' handles actual block)
        const sFile = document.getElementById('student_file').files;
        const mFile = document.getElementById('model_file').files;

        if (sFile.length > 0 && mFile.length > 0) {
            overlay.style.display = 'flex';
        }
    });
});
