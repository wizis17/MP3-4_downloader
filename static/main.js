// Handle form interactions and dynamic content
document.addEventListener('DOMContentLoaded', function() {
    const filetypeSelect = document.getElementById('filetype');
    const qualityDiv = document.getElementById('qualityDiv');
    const audioQualityDiv = document.getElementById('audioQualityDiv');
    const downloadForm = document.getElementById('downloadForm');
    const submitBtn = document.getElementById('submitBtn');
    const loading = document.getElementById('loading');
    const completeMessage = document.getElementById('completeMessage');

    // Toggle quality options based on file type
    function toggleQualityOptions() {
        const filetype = filetypeSelect.value;
        
        if (filetype === 'mp3') {
            qualityDiv.classList.add('hidden');
            audioQualityDiv.classList.remove('hidden');
        } else {
            qualityDiv.classList.remove('hidden');
            audioQualityDiv.classList.add('hidden');
        }
    }

    // Initialize on page load
    toggleQualityOptions();

    // Listen for changes
    filetypeSelect.addEventListener('change', toggleQualityOptions);

    // Handle form submission
    downloadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Show loading state
        submitBtn.style.display = 'none';
        loading.classList.remove('hidden');
        
        // Create FormData and submit
        const formData = new FormData(downloadForm);
        
        fetch('/download', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                return response.blob();
            }
            throw new Error('Download failed');
        })
        .then(blob => {
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'download'; // Will use server-provided filename
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            // Show completion message
            loading.classList.add('hidden');
            completeMessage.classList.remove('hidden');
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Download failed. Please try again.');
            
            // Reset form state
            loading.classList.add('hidden');
            submitBtn.style.display = 'block';
        });
    });

    // URL validation
    const urlInput = document.getElementById('url');
    urlInput.addEventListener('input', function() {
        const url = this.value;
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)/;
        
        if (url && !youtubeRegex.test(url)) {
            this.style.borderColor = '#ef4444';
        } else {
            this.style.borderColor = '#d1d5db';
        }
    });
});