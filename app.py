from flask import Flask, render_template, request, jsonify, Response
import cv2
import numpy as np
import random
import time
import json
import os
from threading import Lock

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'typing-stress-analyzer-secret')

# Global variables for webcam and data storage
camera = None
camera_lock = Lock()
typing_sessions = {}

# Sample paragraphs for typing test
SAMPLE_PARAGRAPHS = [
    "The quick brown fox jumps over the lazy dog. This sentence contains every letter of the alphabet and is commonly used for typing practice.",
    "Technology has revolutionized the way we communicate and work. From smartphones to artificial intelligence, our daily lives are increasingly connected.",
    "Climate change represents one of the most significant challenges of our time. Rising temperatures and extreme weather patterns affect communities worldwide.",
    "The art of cooking combines creativity with science. Understanding heat, timing, and flavor combinations creates memorable culinary experiences.",
    "Space exploration continues to capture human imagination. Missions to Mars and beyond push the boundaries of what we thought possible.",
    "Reading books opens doors to new worlds and perspectives. Literature has the power to educate, inspire, and transform our understanding.",
    "Exercise and physical activity contribute significantly to mental and physical well-being. Regular movement improves mood and cognitive function.",
    "Music transcends cultural boundaries and connects people across different backgrounds. It has the unique ability to evoke emotions and memories."
]

@app.route('/')
def index():
    """Main page with typing test interface"""
    return render_template('index.html')

@app.route('/get_paragraph')
def get_paragraph():
    """Return a random paragraph for typing test"""
    paragraph = random.choice(SAMPLE_PARAGRAPHS)
    return jsonify({'paragraph': paragraph})

@app.route('/submit_results', methods=['POST'])
def submit_results():
    """Process typing test results and stress analysis"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Calculate typing metrics
    wpm = data.get('wpm', 0)
    accuracy = data.get('accuracy', 0)
    typing_time = data.get('typing_time', 0)
    
    # Store session data
    session_id = str(int(time.time()))
    typing_sessions[session_id] = {
        'wpm': wpm,
        'accuracy': accuracy,
        'typing_time': typing_time,
        'stress_level': 'Normal',  # Will be updated with facial analysis
        'timestamp': time.time()
    }
    
    return jsonify({
        'session_id': session_id,
        'wpm': wpm,
        'accuracy': accuracy,
        'stress_level': 'Normal'
    })

@app.route('/video_feed')
def video_feed():
    """Video streaming route for webcam"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames():
    """Generate video frames for streaming"""
    global camera
    
    with camera_lock:
        if camera is None:
            camera = cv2.VideoCapture(0)
            if not camera.isOpened():
                return
    
    while True:
        with camera_lock:
            if camera is None:
                break
            success, frame = camera.read()
            if not success:
                break
            
            # Basic face detection for stress analysis
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            try:
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            except:
                # Fallback if cv2.data is not available
                continue
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            # Draw rectangles around faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                cv2.putText(frame, 'Analyzing...', (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            
            # Encode frame
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/results/<session_id>')
def results(session_id):
    """Display results page"""
    if session_id not in typing_sessions:
        return "Session not found", 404
    
    session_data = typing_sessions[session_id]
    return render_template('results.html', session=session_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)