const socket = io(); // Initialize SocketIO connection

// --- Element References ---
const createRoomCard = document.getElementById('create-room-card');
const joinRoomCard = document.getElementById('join-room-card');
const roomInterface = document.getElementById('room-interface');
const createBtn = document.getElementById('create-btn'); // This is the button you click!
const joinBtn = document.getElementById('join-btn');
const createdCodeDisplay = document.getElementById('created-code');
const roomCodeInput = document.getElementById('room-code-input');
const currentRoomCodeDisplay = document.getElementById('current-room-code');
const userCountDisplay = document.getElementById('user-count');
const sharedFilesList = document.getElementById('shared-files-list');

let currentRoomCode = null;

// --- UI Helper Function ---
function enterRoomView(code) {
    createRoomCard.classList.add('hidden');
    joinRoomCard.classList.add('hidden');
    roomInterface.classList.remove('hidden');
    currentRoomCodeDisplay.textContent = code;
    currentRoomCode = code;
    sharedFilesList.innerHTML = '<li>Fetching available files...</li>';
}

// --- Event Handlers ---

// 1. Create Room Logic: This makes the button work!
createBtn.addEventListener('click', async () => {
    try {
        // 1. Make an AJAX request to the Flask /create_room endpoint
        const response = await fetch('/create_room', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            throw new Error('Failed to create room.');
        }

        const data = await response.json();
        const code = data.code;

        // 2. Display the code and transition to the room interface
        createdCodeDisplay.textContent = `CODE: ${code}`;
        
        // 3. Immediately join the room via SocketIO
        socket.emit('join', { code: code });
        enterRoomView(code); // Switches the UI view

    } catch (error) {
        console.error('Error creating room:', error);
        alert('Could not create room. See console for details.');
    }
});


// 2. Join Room Logic
joinBtn.addEventListener('click', () => {
    const code = roomCodeInput.value.trim().toUpperCase();
    if (code.length === 6) {
        socket.emit('join', { code: code });
        enterRoomView(code); 
    } else {
        alert('Please enter a valid 6-digit room code.');
    }
});


// --- SocketIO Listeners ---

// Handle general room updates (user join/leave)
socket.on('room_update', (data) => {
    userCountDisplay.textContent = `Users online: ${data.count}`;
});

// Handle errors from the server (e.g., non-existent room)
socket.on('error', (data) => {
    console.error('Server error:', data.message);
    alert(`Error: ${data.message}`);
    window.location.reload(); 
});