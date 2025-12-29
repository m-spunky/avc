// Practice Session Page Logic - Updated with Garnet/Champagne theme

let sessionId = null;
let scenarioId = null;
let scenarioData = null;
let mediaRecorder = null;
let recordedChunks = [];
let chunkIndex = 0;
let userStream = null;
let isRecording = false;

// Extract session ID from URL
const pathParts = window.location.pathname.split('/');
sessionId = pathParts[pathParts.length - 1];

// DOM Elements
const scenarioVideo = document.getElementById('scenarioVideo');
const scenarioSource = document.getElementById('scenarioSource');
const userVideo = document.getElementById('userVideo');
const startBtn = document.getElementById('startBtn');
const endBtn = document.getElementById('endBtn');
const statusMessage = document.getElementById('statusMessage');
const recordingIndicator = document.getElementById('recordingIndicator');
const scenarioTitle = document.getElementById('scenarioTitle');
const scenarioDescription = document.getElementById('scenarioDescription');
const stepsContainer = document.getElementById('stepsContainer');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadSessionData();
    await setupUserCamera();

    startBtn.addEventListener('click', startSession);
    endBtn.addEventListener('click', endSession);
});

async function loadSessionData() {
    try {
        // Get session metadata
        const sessionResponse = await fetch(`/storage/scenario_sessions/${sessionId}/metadata.json`);
        const sessionMeta = await sessionResponse.json();
        scenarioId = sessionMeta.scenario_id;

        // Get scenario data
        const scenarioResponse = await fetch(`/api/scenarios/${scenarioId}`);
        scenarioData = await scenarioResponse.json();

        // Update UI
        scenarioTitle.textContent = scenarioData.title;
        scenarioDescription.textContent = scenarioData.description;
        scenarioSource.src = scenarioData.video_path;
        scenarioVideo.load();

        // Render steps
        renderSteps();

    } catch (error) {
        console.error('Failed to load session data:', error);
        statusMessage.textContent = 'Error loading scenario data';
    }
}

function renderSteps() {
    if (!scenarioData.steps) return;

    stepsContainer.innerHTML = scenarioData.steps.map((step, index) => `
        <div class="flex items-start gap-3 p-3 rounded-lg" style="background-color: rgba(120, 28, 46, 0.4);">
            <div class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-semibold" style="background-color: #781C2E; color: #f9e7c9;">
                ${index + 1}
            </div>
            <div class="flex-1">
                <h4 class="font-semibold" style="color: #f9e7c9;">${step.title}</h4>
                <p class="text-sm" style="color: #f9e7c9; opacity: 0.7;">${step.description}</p>
                <p class="text-xs mt-1" style="color: #f9e7c9; opacity: 0.5;">Time: ${formatTime(step.time)}</p>
            </div>
        </div>
    `).join('');
}

async function setupUserCamera() {
    try {
        userStream = await navigator.mediaDevices.getUserMedia({
            video: { width: 1280, height: 720 },
            audio: true
        });

        userVideo.srcObject = userStream;
        statusMessage.textContent = 'Camera ready. Click "Start Practice Session" to begin.';

    } catch (error) {
        console.error('Failed to access camera:', error);
        statusMessage.textContent = 'Error: Could not access camera/microphone';
        startBtn.disabled = true;
    }
}

async function startSession() {
    try {
        // Start recording user
        startRecording();

        // Play scenario video
        scenarioVideo.play();

        // Update UI
        startBtn.classList.add('hidden');
        endBtn.classList.remove('hidden');
        recordingIndicator.classList.remove('hidden');
        statusMessage.textContent = 'Session in progress...';

        // Sync end button with video end
        scenarioVideo.addEventListener('ended', () => {
            statusMessage.textContent = 'Scenario complete. Click "End Session" to view your report.';
        });

    } catch (error) {
        console.error('Failed to start session:', error);
        statusMessage.textContent = 'Error starting session';
    }
}

function startRecording() {
    try {
        const options = { mimeType: 'video/webm;codecs=vp9' };
        mediaRecorder = new MediaRecorder(userStream, options);

        mediaRecorder.ondataavailable = async (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);

                // Upload chunk
                await uploadChunk(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            isRecording = false;
        };

        // Record in chunks (every 5 seconds)
        mediaRecorder.start(5000);
        isRecording = true;

    } catch (error) {
        console.error('Failed to start recording:', error);
    }
}

async function uploadChunk(blob) {
    try {
        const formData = new FormData();
        formData.append('file', blob);
        formData.append('chunk_index', chunkIndex++);

        await fetch(`/api/scenario/upload/${sessionId}`, {
            method: 'POST',
            body: formData
        });

    } catch (error) {
        console.error('Failed to upload chunk:', error);
    }
}

async function endSession() {
    try {
        // Stop recording
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
        }

        // Stop scenario video
        scenarioVideo.pause();

        // Update UI
        endBtn.disabled = true;
        statusMessage.textContent = 'Processing your session...';
        recordingIndicator.classList.add('hidden');

        // Trigger analysis
        const response = await fetch(`/api/scenario/end/${sessionId}`, {
            method: 'POST'
        });

        if (response.ok) {
            // Wait a moment then redirect to report
            statusMessage.textContent = 'Analysis started. Redirecting to report...';

            setTimeout(() => {
                window.location.href = `/scenario_report/${sessionId}`;
            }, 2000);
        } else {
            throw new Error('Failed to end session');
        }

    } catch (error) {
        console.error('Failed to end session:', error);
        statusMessage.textContent = 'Error ending session';
        endBtn.disabled = false;
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}
