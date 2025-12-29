const localVideo = document.getElementById('localVideo');
const remoteVideo = document.getElementById('remoteVideo');
const statusBadge = document.getElementById('statusBadge');
const displaySessionId = document.getElementById('displaySessionId');
const endCallBtn = document.getElementById('endCallBtn');
const recordingBadge = document.getElementById('recordingBadge');

const sessionId = window.location.pathname.split('/').pop();
displaySessionId.innerText = sessionId;

// Generate random participant ID
const participantId = Math.random().toString(36).substring(7);
console.log("My Participant ID:", participantId);

let localStream;
let peerConnection;
let socket;
let mediaRecorder;
const recordedChunks = [];
let uploadInterval;

// STUN configuration
const configuration = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' }
    ]
};

async function start() {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        localVideo.srcObject = localStream;

        // Connect WebSocket
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        socket = new WebSocket(`${protocol}//${window.location.host}/ws/${sessionId}`);

        socket.onopen = () => {
            console.log("WebSocket connected");
            initializePeerConnection();
            socket.send(JSON.stringify({ type: 'join', participantId }));
        };

        socket.onmessage = async (event) => {
            const message = JSON.parse(event.data);
            if (!peerConnection) initializePeerConnection();

            if (message.type === 'offer') {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(message.offer));
                const answer = await peerConnection.createAnswer();
                await peerConnection.setLocalDescription(answer);
                socket.send(JSON.stringify({ type: 'answer', answer }));
            } else if (message.type === 'answer') {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(message.answer));
            } else if (message.type === 'candidate') {
                if (message.candidate) {
                    await peerConnection.addIceCandidate(new RTCIceCandidate(message.candidate));
                }
            } else if (message.type === 'peer-left') {
                // handle peer disconnect
                statusBadge.innerText = "Peer Left";
                statusBadge.classList.replace('text-green-500', 'text-yellow-500');
                statusBadge.classList.replace('bg-green-500/20', 'bg-yellow-500/20');
            } else if (message.type === 'session-ended') {
                console.log("Session ended by peer. Redirecting to report...");
                stopMedia();
                window.location.href = `/report/${sessionId}`;
            }
        };

        socket.onerror = (error) => console.error("WebSocket Error:", error);

        startRecording();

    } catch (e) {
        console.error("Error accessing media devices.", e);
        alert("Camera/Mic permission denied or error.");
    }
}

function initializePeerConnection() {
    if (peerConnection) return;

    peerConnection = new RTCPeerConnection(configuration);

    // Add local tracks
    localStream.getTracks().forEach(track => {
        peerConnection.addTrack(track, localStream);
    });

    // Handle remote stream
    peerConnection.ontrack = (event) => {
        console.log("Received remote track");
        remoteVideo.srcObject = event.streams[0];
        statusBadge.innerText = "Connected";
        statusBadge.classList.replace('text-yellow-500', 'text-green-500');
        statusBadge.classList.replace('bg-yellow-500/20', 'bg-green-500/20');
    };

    // ICE Candidates
    peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
            socket.send(JSON.stringify({ type: 'candidate', candidate: event.candidate }));
        }
    };

    peerConnection.onnegotiationneeded = async () => {
        try {
            const offer = await peerConnection.createOffer();
            await peerConnection.setLocalDescription(offer);
            socket.send(JSON.stringify({ type: 'offer', offer }));
        } catch (e) {
            console.error(e);
        }
    };
}

// --- Recording Logic ---

function startRecording() {
    // Record ONLY local stream for now
    const options = { mimeType: 'video/webm; codecs=vp8,opus' };

    try {
        mediaRecorder = new MediaRecorder(localStream, options);
    } catch (e) {
        console.warn(`VP8 not supported, trying default.`);
        mediaRecorder = new MediaRecorder(localStream);
    }

    mediaRecorder.ondataavailable = handleDataAvailable;
    mediaRecorder.start(5000); // chunk every 5 seconds
    recordingBadge.classList.remove('hidden');
    console.log("Recording started");
}

let chunkIndex = 0;

async function handleDataAvailable(event) {
    if (event.data.size > 0) {
        const chunk = event.data;
        // Upload immediately
        uploadChunk(chunk, chunkIndex++);
    }
}

async function uploadChunk(blob, index) {
    const formData = new FormData();
    formData.append('file', blob);
    formData.append('chunk_index', index);

    try {
        await fetch(`/upload/${sessionId}/${participantId}`, {
            method: 'POST',
            body: formData
        });
        console.log(`Uploaded chunk ${index}`);
    } catch (e) {
        console.error(`Error uploading chunk ${index}`, e);
    }
}

async function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        // Wait a bit for last chunk
    }
}

function stopMedia() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
    if (peerConnection) {
        peerConnection.close();
        peerConnection = null;
    }
    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
    }
}

// --- End Call Logic ---

endCallBtn.addEventListener('click', async () => {
    // Trigger analysis backend - this will notify the other peer too
    try {
        await fetch(`/end_call/${sessionId}`, { method: 'POST' });
        // The broadcast will trigger redirection for US as well via socket
        // but to be safe and immediate:
        stopMedia();
        window.location.href = `/report/${sessionId}`;
    } catch (e) {
        console.error("Error ending call:", e);
        // Fallback cleanup
        stopMedia();
        window.location.href = `/report/${sessionId}`;
    }
});

// Start everything
start();
