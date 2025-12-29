document.addEventListener('DOMContentLoaded', () => {
    const createBtn = document.getElementById('createBtn');
    const joinBtn = document.getElementById('joinBtn');
    const sessionIdInput = document.getElementById('sessionIdInput');

    createBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/create_session', { method: 'POST' });
            const data = await response.json();
            if (data.session_id) {
                window.location.href = `/call/${data.session_id}`;
            }
        } catch (error) {
            console.error('Error creating session:', error);
            alert('Failed to create session');
        }
    });

    joinBtn.addEventListener('click', () => {
        const sessionId = sessionIdInput.value.trim();
        if (sessionId) {
            window.location.href = `/call/${sessionId}`;
        } else {
            alert('Please enter a Session ID');
        }
    });
});
