// Scenario Report Page Logic

let sessionId = null;
let reportData = null;

// Extract session ID from URL
const pathParts = window.location.pathname.split('/');
sessionId = pathParts[pathParts.length - 1];

// DOM Elements
const loadingState = document.getElementById('loadingState');
const reportContent = document.getElementById('reportContent');
const scenarioTitle = document.getElementById('scenarioTitle');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadReport();
});

async function loadReport() {
    try {
        // Poll for report (it might still be processing)
        let attempts = 0;
        const maxAttempts = 60; // 60 seconds max wait

        while (attempts < maxAttempts) {
            const response = await fetch(`/api/scenario/report/${sessionId}`);

            if (response.status === 200) {
                reportData = await response.json();
                renderReport();
                return;
            } else if (response.status === 202) {
                // Still processing
                await new Promise(resolve => setTimeout(resolve, 1000));
                attempts++;
            } else {
                throw new Error('Report not found');
            }
        }

        throw new Error('Report generation timed out');

    } catch (error) {
        console.error('Failed to load report:', error);
        loadingState.innerHTML = `
            <div class="text-center py-12">
                <svg class="w-16 h-16 mx-auto mb-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p class="text-gray-400">Failed to load report. Please try again.</p>
            </div>
        `;
    }
}

function renderReport() {
    // Hide loading, show content
    loadingState.classList.add('hidden');
    reportContent.classList.remove('hidden');

    // Update scenario title
    const sessionMeta = reportData.session_metadata || {};
    scenarioTitle.textContent = `Session: ${sessionMeta.session_id || sessionId}`;

    // Overall metrics
    document.getElementById('confidenceScore').textContent =
        reportData.confidence_score ? reportData.confidence_score.toFixed(1) : '--';

    const audioData = reportData.audio_analysis || {};
    document.getElementById('fluencyScore').textContent =
        audioData.speech_fluency_score ? audioData.speech_fluency_score.toFixed(1) : '--';

    const videoData = reportData.video_analysis || {};
    const emotionalVar = videoData.facial_emotional_variability || 0;
    const emotionalStability = (100 - emotionalVar).toFixed(1);
    document.getElementById('emotionalStability').textContent = emotionalStability;

    // Audio metrics
    document.getElementById('speechRate').textContent =
        audioData.speech_rate_wpm ? `${audioData.speech_rate_wpm} wpm` : '--';
    document.getElementById('pauseFreq').textContent =
        audioData.pause_frequency || '--';
    document.getElementById('voiceStress').textContent =
        audioData.voice_stress_indicator ? audioData.voice_stress_indicator.toFixed(1) : '--';
    document.getElementById('fillerWords').textContent =
        audioData.filler_count || '0';

    // Video metrics
    document.getElementById('dominantEmotion').textContent =
        videoData.dominant_emotion_distribution ?
            Object.keys(videoData.dominant_emotion_distribution)[0] || 'neutral' : 'neutral';
    document.getElementById('emotionalVar').textContent =
        videoData.facial_emotional_variability ? videoData.facial_emotional_variability.toFixed(1) : '--';
    document.getElementById('facialTension').textContent =
        videoData.facial_tension_index ? videoData.facial_tension_index.toFixed(1) : '--';
    document.getElementById('expressiveness').textContent =
        videoData.facial_expressiveness_score ? videoData.facial_expressiveness_score.toFixed(1) : '--';

    // Render step-wise analysis
    renderStepwiseAnalysis();

    // Render insights
    renderInsights();
}

function renderStepwiseAnalysis() {
    const stepwiseData = reportData.stepwise_analysis || [];
    const container = document.getElementById('stepwiseContainer');

    if (stepwiseData.length === 0) {
        container.innerHTML = '<p class="text-gray-400">No step-wise data available</p>';
        return;
    }

    container.innerHTML = stepwiseData.map((stepData, index) => {
        const step = stepData.step || {};
        const metrics = stepData.metrics || {};
        const emotionDist = metrics.emotion_distribution || {};

        // Get top emotion
        const topEmotion = Object.entries(emotionDist)
            .sort((a, b) => b[1] - a[1])[0] || ['neutral', 0];

        return `
            <div class="bg-gray-700 rounded-lg p-4">
                <div class="flex items-start gap-4">
                    <div class="flex-shrink-0 w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center font-bold">
                        ${index + 1}
                    </div>
                    <div class="flex-1">
                        <h4 class="font-semibold text-lg mb-1">${step.title || `Step ${index + 1}`}</h4>
                        <p class="text-sm text-gray-400 mb-3">${step.description || ''}</p>
                        
                        <div class="grid grid-cols-2 gap-3 text-sm">
                            <div>
                                <span class="text-gray-400">Dominant Emotion:</span>
                                <span class="ml-2 font-semibold capitalize">${topEmotion[0]}</span>
                            </div>
                            <div>
                                <span class="text-gray-400">Samples:</span>
                                <span class="ml-2 font-semibold">${metrics.sample_count || 0}</span>
                            </div>
                        </div>
                        
                        ${Object.keys(emotionDist).length > 0 ? `
                            <div class="mt-3">
                                <p class="text-xs text-gray-400 mb-2">Emotion Distribution:</p>
                                <div class="flex gap-2 flex-wrap">
                                    ${Object.entries(emotionDist).map(([emotion, percent]) => `
                                        <span class="px-2 py-1 bg-gray-600 rounded text-xs">
                                            ${emotion}: ${percent.toFixed(1)}%
                                        </span>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function renderInsights() {
    const summary = reportData.summary || {};
    const strengths = summary.detected_strengths || [];
    const observationalSummary = summary.observational_summary || '';
    const container = document.getElementById('insightsContainer');

    let html = '';

    if (observationalSummary) {
        html += `
            <div class="p-4 bg-gray-700 rounded-lg">
                <h4 class="font-semibold mb-2">Session Summary</h4>
                <p class="text-gray-300">${observationalSummary}</p>
            </div>
        `;
    }

    if (strengths.length > 0) {
        html += `
            <div class="p-4 bg-gray-700 rounded-lg">
                <h4 class="font-semibold mb-2">Detected Strengths</h4>
                <ul class="space-y-1">
                    ${strengths.map(strength => `
                        <li class="flex items-start gap-2">
                            <svg class="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                            </svg>
                            <span class="text-gray-300">${strength}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    }

    if (!html) {
        html = '<p class="text-gray-400">No insights available yet</p>';
    }

    container.innerHTML = html;
}
