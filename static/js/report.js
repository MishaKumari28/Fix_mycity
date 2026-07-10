/**
 * FixMyCity — Report Page JS
 * Handles: image upload preview, drag-drop, live camera, geolocation, form submission
 */

// ── Image Tab Switching ───────────────────────────────────────────
function switchTab(tab) {
  const tabs = ['upload', 'camera'];
  tabs.forEach(t => {
    document.getElementById(`pane-${t}`).classList.toggle('d-none', t !== tab);
    document.getElementById(`tab-${t}`).classList.toggle('active', t === tab);
  });
  if (tab === 'camera') { /* don't auto-start; let user click */ }
  else { stopCamera(); }
}

// ── File Upload Preview ───────────────────────────────────────────
const imageInput = document.getElementById('imageInput');
if (imageInput) {
  imageInput.addEventListener('change', e => {
    const file = e.target.files[0];
    if (file) showPreview(URL.createObjectURL(file));
  });
}

function showPreview(src) {
  document.getElementById('previewImg').src = src;
  document.getElementById('imagePreview').classList.remove('d-none');
  document.getElementById('dropZone').classList.add('d-none');
}

function clearImage() {
  imageInput.value = '';
  document.getElementById('imagePreview').classList.add('d-none');
  document.getElementById('dropZone').classList.remove('d-none');
}

// ── Drag & Drop ───────────────────────────────────────────────────
const dropZone = document.getElementById('dropZone');
if (dropZone) {
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave',  () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      const dt = new DataTransfer();
      dt.items.add(file);
      imageInput.files = dt.files;
      showPreview(URL.createObjectURL(file));
    }
  });
  dropZone.addEventListener('click', () => imageInput.click());
}

// ── Live Camera ───────────────────────────────────────────────────
let mediaStream = null;

function startCamera() {
  navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
    .then(stream => {
      mediaStream = stream;
      const video = document.getElementById('cameraFeed');
      video.srcObject = stream;
      document.getElementById('startCameraBtn').classList.add('d-none');
      document.getElementById('snapBtn').classList.remove('d-none');
      document.getElementById('stopCameraBtn').classList.remove('d-none');
    })
    .catch(err => {
      showToast('Camera access denied: ' + err.message, 'danger');
    });
}

function snapPhoto() {
  const video  = document.getElementById('cameraFeed');
  const canvas = document.getElementById('cameraCanvas');
  canvas.width  = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
  document.getElementById('capturedImg').src = dataUrl;
  document.getElementById('capturedImageData').value = dataUrl;
  document.getElementById('cameraCapture').classList.remove('d-none');
  stopCamera();
}

function stopCamera() {
  if (mediaStream) {
    mediaStream.getTracks().forEach(t => t.stop());
    mediaStream = null;
  }
  const video = document.getElementById('cameraFeed');
  if (video) video.srcObject = null;
  const snapBtn = document.getElementById('snapBtn');
  const stopBtn = document.getElementById('stopCameraBtn');
  const startBtn = document.getElementById('startCameraBtn');
  if (snapBtn)  snapBtn.classList.add('d-none');
  if (stopBtn)  stopBtn.classList.add('d-none');
  if (startBtn) startBtn.classList.remove('d-none');
}

function clearCapture() {
  document.getElementById('capturedImageData').value = '';
  document.getElementById('capturedImg').src = '';
  document.getElementById('cameraCapture').classList.add('d-none');
  startCamera();
}

// ── Geolocation ───────────────────────────────────────────────────
function detectLocation() {
  const icon   = document.getElementById('locIcon');
  const status = document.getElementById('locStatus');
  const statusText = document.getElementById('locStatusText');

  icon.className = 'bi bi-arrow-repeat me-2 spin';

  if (!navigator.geolocation) {
    showToast('Geolocation not supported by your browser.', 'warning');
    icon.className = 'bi bi-crosshair me-2';
    return;
  }

  navigator.geolocation.getCurrentPosition(
    pos => {
      const { latitude: lat, longitude: lng, accuracy } = pos.coords;
      document.getElementById('latInput').value = lat.toFixed(6);
      document.getElementById('lngInput').value = lng.toFixed(6);

      // Reverse geocode using Nominatim (free, no key needed)
      fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`)
        .then(r => r.json())
        .then(data => {
          const addr = data.display_name || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
          document.getElementById('locationInput').value = addr;
          statusText.textContent = `GPS locked (±${Math.round(accuracy)}m)`;
          status.classList.remove('d-none');
          showToast('Location detected!', 'success');
        })
        .catch(() => {
          document.getElementById('locationInput').value = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
          statusText.textContent = `Coordinates: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
          status.classList.remove('d-none');
        });
      icon.className = 'bi bi-crosshair me-2';
    },
    err => {
      showToast('Could not get location: ' + err.message, 'warning');
      icon.className = 'bi bi-crosshair me-2';
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}

// ── Character Counter ─────────────────────────────────────────────
const desc = document.getElementById('description');
const counter = document.getElementById('charCount');
if (desc && counter) {
  desc.addEventListener('input', () => {
    counter.textContent = desc.value.length;
    if (desc.value.length > 450) counter.style.color = 'var(--fmc-danger)';
    else counter.style.color = '';
  });
}

// ── Sensitive Category Guard ──────────────────────────────────────
const catHint = document.getElementById('categoryHint');
if (catHint) {
  const SENSITIVE = ['domestic_violence','sexual_harassment','child_abuse','human_trafficking','personal_safety'];
  catHint.addEventListener('change', () => {
    if (SENSITIVE.includes(catHint.value)) {
      window.location.href = `/sensitive?category=${catHint.value}`;
    }
  });
}

// ── Form Submit ───────────────────────────────────────────────────
const reportForm = document.getElementById('reportForm');
if (reportForm) {
  reportForm.addEventListener('submit', e => {
    const btn = document.getElementById('submitBtn');
    btn.classList.add('loading');
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Analysing with AI…';
    // If camera capture was used, inject as hidden field
    const capturedData = document.getElementById('capturedImageData');
    if (capturedData && capturedData.value && (!imageInput || !imageInput.files.length)) {
      // Convert base64 dataURL to a file for FormData
      const blob = dataURLtoBlob(capturedData.value);
      const dt = new DataTransfer();
      dt.items.add(new File([blob], 'capture.jpg', { type: 'image/jpeg' }));
      if (imageInput) imageInput.files = dt.files;
    }
  });
}

function dataURLtoBlob(dataURL) {
  const [header, data] = dataURL.split(',');
  const mime = header.match(/:(.*?);/)[1];
  const binary = atob(data);
  const array = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) array[i] = binary.charCodeAt(i);
  return new Blob([array], { type: mime });
}

// ── Add spin CSS dynamically ──────────────────────────────────────
const spinStyle = document.createElement('style');
spinStyle.textContent = `.spin { animation: spin .8s linear infinite; display: inline-block; }`;
document.head.appendChild(spinStyle);
