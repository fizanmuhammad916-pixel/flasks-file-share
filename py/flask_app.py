import random
import string
import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room, emit

# --- Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_secret_key'
socketio = SocketIO(app)

# Define the upload folder and ensure it exists
UPLOAD_FOLDER = 'uploaded_files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Dictionary to store active room codes and their states
# ROOMS[code] = {'clients': {sid: 'username', ...}, 'files': [{'name': 'file.txt', 'unique_name': 'code_file.txt'}, ...]}
ROOMS = {}
# Dictionary to map session IDs (sids) to the room code they are in
CLIENT_ROOM_MAP = {}

# --- Helper Functions ---
def generate_unique_code(length=6):
    """Generates a unique, uppercase room code."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if code not in ROOMS:
            return code

# --- Routes ---
@app.route('/')
def index():
    """Renders the main creation/join page."""
    return render_template('index.html')

@app.route('/create_room', methods=['POST'])
def create_room():
    """Endpoint to generate and return a new room code."""
    code = generate_unique_code()
    ROOMS[code] = {'clients': {}, 'files': []} 
    print(f"Room created: {code}")
    return jsonify({'code': code})

@app.route('/upload', methods=['POST'])
def upload_file():
    """Receives file, saves it temporarily, and broadcasts 'file_available'."""
    if 'file' not in request.files or 'room_code' not in request.form:
        return jsonify({'error': 'Missing file or room code'}), 400

    file = request.files['file']
    room_code = request.form['room_code'].upper()

    if room_code not in ROOMS or file.filename == '':
        return jsonify({'error': 'Invalid room or no file selected'}), 400

    # Generate a unique filename using room code as prefix
    unique_filename = f"{room_code}_{file.filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(file_path)

    # Update the room state
    file_record = {
        'name': file.filename,
        'unique_name': unique_filename,
    }
    ROOMS[room_code]['files'].append(file_record)
    
    # Broadcast to the room that a new file is available
    socketio.emit('file_available', {'file': file_record}, room=room_code)
    print(f"File '{file.filename}' uploaded to room {room_code}")

    return jsonify({'message': 'File uploaded successfully', 'file': file_record})

@app.route('/download/<unique_filename>', methods=['GET'])
def download_file(unique_filename):
    """Serves the temporary file from the secure upload directory."""
    if '_' not in unique_filename:
        return "Invalid file request.", 400
    return send_from_directory(app.config['UPLOAD_FOLDER'], unique_filename, as_attachment=True)

# --- SocketIO Events ---
@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('join')
def on_join(data):
    room_code = data.get('code', '').upper()
    
    if room_code not in ROOMS:
        emit('error', {'message': f'Room {room_code} does not exist.'}, room=request.sid)
        return

    join_room(room_code)
    CLIENT_ROOM_MAP[request.sid] = room_code
    ROOMS[room_code]['clients'][request.sid] = 'Anonymous'

    client_count = len(ROOMS[room_code]['clients'])
    
    emit('room_update', 
         {'message': f'A user joined the room.', 
          'count': client_count}, 
         room=room_code)
    
    emit('initial_files', {'files': ROOMS[room_code]['files']}, room=request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    room_code = CLIENT_ROOM_MAP.pop(sid, None)

    if room_code and room_code in ROOMS:
        ROOMS[room_code]['clients'].pop(sid, None)
        leave_room(room_code)

        client_count = len(ROOMS[room_code]['clients'])

        if client_count == 0:
            # Cleanup: Delete files associated with the room
            files_to_delete = [f['unique_name'] for f in ROOMS[room_code].get('files', [])]
            for unique_name in files_to_delete:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
                except OSError as e:
                    print(f"Error deleting file {unique_name}: {e}")
                    
            del ROOMS[room_code]
            print(f"Room {room_code} is empty and has been deleted, along with its files.")
        else:
            emit('room_update', 
                 {'message': f'A user left the room.', 
                  'count': client_count}, 
                 room=room_code)

if __name__ == '__main__':
    # Run server
    socketio.run(app, debug=True)