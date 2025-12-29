const sessionId = window.location.pathname.split('/').pop();
document.getElementById('sessionIdDisplay').innerText = sessionId;

const statusIndicator = document.getElementById('statusIndicator');
const contentDiv = document.getElementById('content');
const downloadSection = document.getElementById('downloadSection');

// Poll for report
async function checkReport() {
    try {
        const response = await fetch(`/api/report/${sessionId}`);

        if (response.status === 202) {
            // Still processing
            setTimeout(checkReport, 2000); // Retry every 2s
            return;
        }

        if (response.status === 200) {
            const data = await response.json();
            renderReport(data);
        } else {
            statusIndicator.innerText = "Report not found or error.";
            statusIndicator.className = "px-4 py-2 bg-red-500/20 text-red-500 rounded-lg";
        }
    } catch (e) {
        console.error(e);
    }
}

function renderReport(data) {
    statusIndicator.innerText = "Analysis Completed";
    statusIndicator.className = "px-4 py-2 bg-green-500/20 text-green-500 rounded-lg";
    statusIndicator.classList.remove('animate-pulse');

    contentDiv.classList.remove('hidden');
    downloadSection.classList.remove('hidden');

    // Set download links
    document.getElementById('downloadVideoBtn').href = `/storage/${sessionId}/merged/full_session.mp4`;
    document.getElementById('downloadJsonBtn').href = `/storage/${sessionId}/report/report.json`;

    // 1. Audio Data
    const audio = data.audio_analysis;
    if (audio) {
        document.getElementById('fillerCount').innerText = audio.filler_count;
        document.getElementById('longPauses').innerText = audio.pause_frequency; // Using pause_frequency as longPauses
        document.getElementById('transcriptText').innerText = audio.transcript || "No speech detected.";
    }

    // 2. Video Data Check
    const videoAnalysis = data.video_analysis || {};
    const participantsData = videoAnalysis.participants || {};
    const participantsIds = Object.keys(participantsData);

    if (participantsIds.length > 0) {
        // Create participant selector if there are multiple
        if (participantsIds.length > 1) {
            setupParticipantSelector(participantsData, participantsIds);
        }

        // Render first participant by default
        renderParticipantData(participantsData[participantsIds[0]]);
    }
}

function setupParticipantSelector(participantsData, ids) {
    let selector = document.getElementById('participantSelector');
    if (!selector) {
        const container = document.getElementById('participantSelectorContainer');
        const label = document.createElement('span');
        label.innerText = "Select Participant: ";
        label.className = "text-sm mr-2";
        container.appendChild(label);

        selector = document.createElement('select');
        selector.id = 'participantSelector';
        selector.className = 'bg-slate-800 text-white border border-slate-700 rounded px-2 py-1 text-sm outline-none focus:border-primary';

        ids.forEach(id => {
            const option = document.createElement('option');
            option.value = id;
            option.innerText = `Participant: ${id}`;
            selector.appendChild(option);
        });

        selector.addEventListener('change', (e) => {
            renderParticipantData(participantsData[e.target.value]);
        });

        container.appendChild(selector);
    }
}

let emotionChartInstance = null;
let gazeChartInstance = null;

function renderParticipantData(vData) {
    if (!vData) return;

    // Emotion Chart
    const ctxEmotion = document.getElementById('emotionChart').getContext('2d');
    const emotions = vData.emotions || [];
    const emotionCounts = vData.emotion_summary || {};

    if (emotionChartInstance) emotionChartInstance.destroy();

    emotionChartInstance = new Chart(ctxEmotion, {
        type: 'bar',
        data: {
            labels: Object.keys(emotionCounts),
            datasets: [{
                label: 'Emotion Frequency',
                data: Object.values(emotionCounts),
                backgroundColor: 'rgba(120, 28, 46, 0.5)', // Garnet hint
                borderColor: '#781C2E',
                borderWidth: 1
            }]
        },
        options: {
            scales: { y: { beginAtZero: true } },
            plugins: {
                legend: { labels: { color: '#f9e7c9' } }
            }
        }
    });

    // Gaze Chart
    const ctxGaze = document.getElementById('gazeChart').getContext('2d');
    const gaze = vData.gaze_counts || {};

    if (gazeChartInstance) gazeChartInstance.destroy();

    gazeChartInstance = new Chart(ctxGaze, {
        type: 'doughnut',
        data: {
            labels: Object.keys(gaze),
            datasets: [{
                data: Object.values(gaze),
                backgroundColor: [
                    '#781C2E', '#a12b3f', '#c94056', '#f25a72', '#ff8499'
                ]
            }]
        },
        options: {
            plugins: {
                legend: { labels: { color: '#f9e7c9' } }
            }
        }
    });
}

// Start polling
checkReport();
