const TOKEN_KEY = 'digame_device_token';

const requestContainer = document.getElementById('request-container');
const approvedContainer = document.getElementById('approved-container');
const requestButton = document.getElementById('request-access');
const recordButton = document.getElementById('record-button');
const stopButton = document.getElementById('stop-button');
const feedback = document.getElementById('feedback');
const timerDisplay = document.getElementById('timer');
const queueInfo = document.getElementById('queue-info');
const deviceNameInput = document.getElementById('device-name');

function apiPath(path) {
  return path;
}

let recorder = null;
let currentStream = null;
let chunks = [];
let timer = null;
let seconds = 0;
const MAX_SECONDS = 10;

function setFeedback(message, type = 'info') {
  feedback.textContent = message;
  feedback.className = type === 'error' ? 'status error' : 'status';
}

function formatTime(sec) {
  const minutes = String(Math.floor(sec / 60)).padStart(2, '0');
  const secondsText = String(sec % 60).padStart(2, '0');
  return `${minutes}:${secondsText}`;
}

async function fetchJson(path, options = {}) {
  const response = await fetch(path, options);
  return response.json();
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function saveToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

async function updateStatus() {
  setFeedback('Cargando estado...');
  requestContainer.style.display = 'none';
  approvedContainer.style.display = 'none';
  queueInfo.style.display = 'none';

  const token = getToken();
  const query = token ? `?token=${encodeURIComponent(token)}` : '';
  const status = await fetchJson(apiPath('/api/digame/access/status') + query);
  const system = await fetchJson(apiPath('/api/digame/status'));

  if (!status || status.status === 'not_authorized') {
    setFeedback('No estás autorizado. Solicita acceso para grabar.', 'info');
    requestContainer.style.display = 'block';
    queueInfo.style.display = 'block';
    queueInfo.innerHTML = `Sistema: ${system.system_status}. Cola ${system.queue_length}/${system.queue_max}.`; 
    return;
  }

  if (status.status === 'pending') {
    setFeedback('Solicitud pendiente. Espera aprobación del administrador.', 'info');
    requestContainer.style.display = 'block';
    deviceNameInput.value = status.name || '';
    queueInfo.style.display = 'block';
    queueInfo.innerHTML = `Sistema: ${system.system_status}. Cola ${system.queue_length}/${system.queue_max}.`;
    return;
  }

  if (status.status === 'approved') {
    setFeedback('Autorizado. Ya puedes grabar.', 'info');
    approvedContainer.style.display = 'block';
    queueInfo.style.display = 'block';
    queueInfo.innerHTML = `Sistema: ${system.system_status}. Cola ${system.queue_length}/${system.queue_max}.`;
    return;
  }

  if (status.status === 'rejected' || status.status === 'revoked') {
    setFeedback(`Acceso ${status.status}. Puedes solicitarlo de nuevo.`, 'error');
    requestContainer.style.display = 'block';
    queueInfo.style.display = 'block';
    queueInfo.innerHTML = `Sistema: ${system.system_status}. Cola ${system.queue_length}/${system.queue_max}.`;
    return;
  }

  setFeedback('Estado desconocido.', 'error');
  requestContainer.style.display = 'block';
}

async function requestAccess() {
  try {
    const token = getToken();
    const body = { token, name: deviceNameInput.value.trim() };
    const response = await fetch(apiPath('/api/digame/access/request'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await response.json();
    if (data.token) {
      saveToken(data.token);
      updateStatus();
    } else {
      setFeedback('No se pudo solicitar acceso.', 'error');
    }
  } catch (err) {
    setFeedback('Error al solicitar acceso.', 'error');
  }
}

function resetTimer() {
  clearInterval(timer);
  seconds = 0;
  timerDisplay.textContent = formatTime(0);
}

function beginRecording(stream) {
  recorder = new MediaRecorder(stream);
  currentStream = stream;
  chunks = [];

  recorder.addEventListener('dataavailable', event => {
    if (event.data.size > 0) {
      chunks.push(event.data);
    }
  });

  recorder.addEventListener('stop', async () => {
    if (currentStream) {
      currentStream.getTracks().forEach(track => track.stop());
      currentStream = null;
    }

    const blob = new Blob(chunks, { type: 'audio/webm' });
    if (!blob.size) {
      setFeedback('Audio vacío. Vuelve a intentarlo.', 'error');
      return;
    }

    stopButton.disabled = true;
    recordButton.disabled = false;
    setFeedback('Subiendo audio...', 'info');

    const form = new FormData();
    form.append('audio', blob, 'digame.webm');
    const token = getToken();
    const response = await fetch(apiPath('/api/digame/audio'), {
      method: 'POST',
      headers: token ? { 'X-DIGAME-TOKEN': token } : {},
      body: form
    });
    const result = await response.json();
    if (response.ok) {
      setFeedback('Audio enviado y añadido a la cola.', 'info');
      queueInfo.innerHTML += '<br>Audio enviado.';
      setTimeout(updateStatus, 1000);
    } else {
      setFeedback(result.error || 'Error al enviar audio.', 'error');
    }
  });

  recorder.start();
  recordButton.disabled = true;
  stopButton.disabled = false;
  setFeedback('Grabando…', 'info');
  seconds = 0;
  timerDisplay.textContent = formatTime(seconds);
  timer = setInterval(() => {
    seconds += 1;
    timerDisplay.textContent = formatTime(seconds);
    if (seconds >= MAX_SECONDS) {
      stopRecording();
    }
  }, 1000);
}

async function startRecording() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setFeedback('Tu navegador no soporta grabación de audio.', 'error');
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    beginRecording(stream);
  } catch (err) {
    setFeedback('No se pudo acceder al micrófono.', 'error');
  }
}

function stopRecording() {
  if (!recorder || recorder.state !== 'recording') {
    return;
  }
  recorder.stop();
  clearInterval(timer);
  timerDisplay.textContent = formatTime(seconds);
  stopButton.disabled = true;
}

requestButton.addEventListener('click', requestAccess);
recordButton.addEventListener('click', startRecording);
stopButton.addEventListener('click', stopRecording);

updateStatus();
