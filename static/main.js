const form = document.getElementById('downloadForm');
const loading = document.getElementById('loading');
const submitBtn = document.getElementById('submitBtn');
const completeMessage = document.getElementById('completeMessage');
const filetype = document.getElementById('filetype');
const qualityDiv = document.getElementById('qualityDiv');
const audioQualityDiv = document.getElementById('audioQualityDiv');

function toggleQuality() {
  if (filetype.value === 'mp4') {
    qualityDiv.classList.remove('hidden');
    audioQualityDiv.classList.add('hidden');
  } else {
    qualityDiv.classList.add('hidden');
    audioQualityDiv.classList.remove('hidden');
  }
}

filetype.addEventListener('change', toggleQuality);
window.addEventListener('DOMContentLoaded', toggleQuality);

form.addEventListener('submit', () => {
  loading.classList.remove('hidden');
  submitBtn.disabled = true;
  submitBtn.classList.add('opacity-50', 'cursor-not-allowed');

  setTimeout(() => {
    loading.classList.add('hidden');
    completeMessage.classList.remove('hidden');
  }, 3000); // Demo only
});