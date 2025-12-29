// Scenario Selection Page Logic

let scenarios = [];

// Load scenarios on page load
document.addEventListener('DOMContentLoaded', async () => {
    await loadScenarios();
});

async function loadScenarios() {
    try {
        const response = await fetch('/api/scenarios');
        const data = await response.json();
        scenarios = data.scenarios || [];

        renderScenarios();
    } catch (error) {
        console.error('Failed to load scenarios:', error);
        showError('Failed to load scenarios. Please try again.');
    }
}

function renderScenarios() {
    const container = document.getElementById('scenariosContainer');
    const emptyState = document.getElementById('emptyState');

    if (scenarios.length === 0) {
        container.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');

    container.innerHTML = scenarios.map(scenario => `
        <div class="rounded-xl overflow-hidden shadow-2xl transition-all duration-300 hover:scale-105" style="background-color: rgba(120, 28, 46, 0.3); backdrop-filter: blur(10px);">
            <div class="relative bg-black" style="aspect-ratio: 16/9;">
                <video class="w-full h-full object-cover" muted>
                    <source src="${scenario.video_path}" type="video/mp4">
                </video>
                <div class="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent"></div>
                <div class="absolute bottom-4 left-4 right-4">
                    <h3 class="text-xl font-bold mb-1" style="color: #f9e7c9;">${scenario.title}</h3>
                    <p class="text-sm" style="color: #f9e7c9; opacity: 0.8;">${formatDuration(scenario.duration)}</p>
                </div>
            </div>
            
            <div class="p-6">
                <p class="mb-4 line-clamp-2" style="color: #f9e7c9; opacity: 0.9;">${scenario.description}</p>
                
                <div class="mb-4">
                    <div class="flex items-center gap-2 text-sm mb-2" style="color: #f9e7c9; opacity: 0.7;">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
                        </svg>
                        <span>${scenario.steps ? scenario.steps.length : 0} Steps</span>
                    </div>
                </div>
                
                <button onclick="startScenario('${scenario.id}')" 
                        class="w-full px-4 py-3 rounded-lg font-semibold transition-all duration-200"
                        style="background-color: #781C2E; color: #f9e7c9;"
                        onmouseover="this.style.backgroundColor='#5a1522'; this.style.boxShadow='0 10px 25px rgba(120, 28, 46, 0.5)'"
                        onmouseout="this.style.backgroundColor='#781C2E'; this.style.boxShadow='none'">
                    Start Practice →
                </button>
            </div>
        </div>
    `).join('');
}

async function startScenario(scenarioId) {
    try {
        // Create new session
        const response = await fetch('/api/scenario/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scenario_id: scenarioId })
        });

        const data = await response.json();

        if (data.session_id) {
            // Redirect to practice page
            window.location.href = `/practice/${data.session_id}`;
        } else {
            throw new Error('Failed to create session');
        }
    } catch (error) {
        console.error('Failed to start scenario:', error);
        showError('Failed to start practice session. Please try again.');
    }
}

function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function showError(message) {
    alert(message); // Simple error display
}
