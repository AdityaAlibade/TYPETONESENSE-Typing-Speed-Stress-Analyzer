from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import random
import time
import json
import os
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'typing-stress-analyzer-secret')

# Global variables for data storage
typing_sessions = {}
stress_data = {}

# Initialize face cascade once
try:
    import cv2
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    if face_cascade.empty():
        face_cascade = None
except Exception:
    face_cascade = None

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
    
    # Use session ID from frontend or generate fallback
    session_id = data.get('session_id', str(int(time.time())))
    
    # Calculate average stress level from collected data
    avg_stress_level = 'Normal'
    if session_id in stress_data and stress_data[session_id]:
        stress_levels = [item['stress_level'] for item in stress_data[session_id]]
        # Get most common stress level
        stress_counts = {}
        for level in stress_levels:
            stress_counts[level] = stress_counts.get(level, 0) + 1
        if stress_counts:
            avg_stress_level = max(stress_counts.keys(), key=lambda k: stress_counts[k])
        else:
            avg_stress_level = 'Normal'
    
    typing_sessions[session_id] = {
        'wpm': wpm,
        'accuracy': accuracy,
        'typing_time': typing_time,
        'stress_level': avg_stress_level,
        'timestamp': time.time()
    }
    
    return jsonify({
        'session_id': session_id,
        'wpm': wpm,
        'accuracy': accuracy,
        'stress_level': avg_stress_level
    })

@app.route('/analyze_frame', methods=['POST'])
def analyze_frame():
    """Analyze a video frame for stress detection"""
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400
        
        session_id = data.get('session_id', 'default')
        
        # Decode base64 image
        image_data = data['image'].split(',')[1]  # Remove data:image/jpeg;base64, prefix
        image_bytes = base64.b64decode(image_data)
        
        # Convert to OpenCV format
        pil_image = Image.open(BytesIO(image_bytes))
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        # Analyze stress level
        stress_level = analyze_facial_stress(cv_image)
        
        # Store stress data for session
        if session_id not in stress_data:
            stress_data[session_id] = []
        stress_data[session_id].append({
            'timestamp': time.time(),
            'stress_level': stress_level
        })
        
        return jsonify({
            'stress_level': stress_level,
            'status': 'success'
        })
        
    except Exception as e:
        print(f"Error analyzing frame: {e}")
        return jsonify({'error': 'Failed to analyze frame'}), 500

def analyze_facial_stress(frame):
    """Analyze facial features for stress indicators"""
    if face_cascade is None:
        return 'Unknown'
    
    try:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5, minSize=(30, 30))
        
        if len(faces) == 0:
            return 'No Face Detected'
        
        # Simple stress analysis based on face characteristics
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            
            # Calculate facial metrics for stress detection
            face_height, face_width = face_roi.shape
            face_area = face_height * face_width
            
            # Simple heuristics for stress detection
            # In a real implementation, you'd use more sophisticated ML models
            
            # Check for eye region intensity (stress can cause changes)
            eye_region = face_roi[int(face_height*0.2):int(face_height*0.5), :]
            eye_intensity = np.mean(eye_region)
            
            # Check mouth region (stress can affect mouth position)
            mouth_region = face_roi[int(face_height*0.6):int(face_height*0.8), :]
            mouth_intensity = np.mean(mouth_region)
            
            # Simple classification based on facial metrics
            if eye_intensity < 100 and mouth_intensity < 120:
                return 'Tense'
            elif eye_intensity > 140:
                return 'Happy'
            elif mouth_intensity < 100:
                return 'Focused'
            else:
                return 'Normal'
        
        return 'Normal'
        
    except Exception as e:
        print(f"Error in stress analysis: {e}")
        return 'Unknown'

@app.route('/results/<session_id>')
def results(session_id):
    """Display results page"""
    if session_id not in typing_sessions:
        return "Session not found", 404
    
    session_data = typing_sessions[session_id]
    return render_template('results.html', session=session_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)