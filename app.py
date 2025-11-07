from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from collections import Counter
import cv2
import numpy as np
from PIL import Image
import base64
import random
import time
import json
import os
from io import BytesIO
from typing import Dict, List, Optional
from face_analyzer import FaceAnalyzer, TypingSession, StressSample, EmotionLabel

# Initialize Flask with compression and caching
app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = os.environ.get('SESSION_SECRET', 'typing-stress-analyzer-secret')

# Try to enable gzip/brotli compression if Flask-Compress is available.
# This allows the app to run even if the optional dependency fails to build.
try:
    from flask_compress import Compress
    Compress(app)
    print("Flask-Compress enabled")
except Exception as e:
    # Do not fail if compression isn't available (e.g., brotli build tools missing)
    print(f"Flask-Compress not enabled: {e}")

# Setup caching headers for static files
@app.after_request
def add_header(response):
    if 'Cache-Control' not in response.headers:
        if request.path.startswith('/static/'):
            # Cache static files for 1 hour
            response.headers['Cache-Control'] = 'public, max-age=3600'
        else:
            # No cache for dynamic content
            response.headers['Cache-Control'] = 'no-store'
    return response

# Global variables for data storage
typing_sessions = {}
stress_data = {}

# last processed debug image bytes (JPEG) for troubleshooting
last_debug_image = None

# Initialize face cascade once
try:
    import cv2
    import sys
    print(f"OpenCV version: {cv2.__version__}")
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    print(f"Loading cascade from: {cascade_path}")
    
    if not os.path.exists(cascade_path):
        print(f"Error: Cascade file not found at {cascade_path}")
        alternative_paths = [
            './haarcascade_frontalface_default.xml',
            os.path.join(os.path.dirname(__file__), 'haarcascade_frontalface_default.xml')
        ]
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                print(f"Found cascade at alternative path: {alt_path}")
                cascade_path = alt_path
                break
    
    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        print("Error: Failed to load cascade classifier")
        face_cascade = None
    else:
        print("Successfully loaded face cascade classifier")
except Exception as e:
    print(f"Error initializing OpenCV: {str(e)}")
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
    """Main landing page"""
    return render_template('index.html')

@app.route('/test')
def test():
    """Main typing test interface"""
    return render_template('test.html')

@app.route('/about')
def about():
    """About page with team information"""
    return render_template('about.html')

@app.route('/contact')
def contact():
    """Contact page with form"""
    return render_template('contact.html')

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

    # Calculate progress points (always create these so template JS has data)
    progress_points = [
        0,  # start
        int(wpm * 0.6),  # 25% point
        int(wpm * 0.8),  # 50% point
        int(wpm * 0.9),  # 75% point
        wpm   # end
    ]

    typing_sessions[session_id] = {
        'wpm': wpm,
        'accuracy': accuracy,
        'typing_time': typing_time,
        'stress_level': avg_stress_level,
        'timestamp': time.time(),
        'progress': progress_points
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
        
        # Validate image data format
        image_data = data['image']
        if not image_data.startswith('data:image/jpeg;base64,'):
            return jsonify({'error': 'Invalid image format'}), 400
        
        # Decode base64 image
        try:
            image_data = image_data.split(',')[1]  # Remove data:image/jpeg;base64, prefix
            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            print(f"Base64 decode error: {e}")
            return jsonify({'error': 'Invalid base64 encoding'}), 400
        
        # Convert to PIL Image
        try:
            pil_image = Image.open(BytesIO(image_bytes))
            if pil_image.size[0] == 0 or pil_image.size[1] == 0:
                return jsonify({'error': 'Invalid image dimensions'}), 400
        except Exception as e:
            print(f"PIL processing error: {e}")
            return jsonify({'error': 'Failed to process image'}), 400
        
        # Convert to OpenCV format
        try:
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            if cv_image.size == 0:
                return jsonify({'error': 'Failed to convert to OpenCV format'}), 400
        except Exception as e:
            print(f"OpenCV conversion error: {e}")
            return jsonify({'error': 'Failed to convert image format'}), 400
        
        # Check if face detection is available
        if face_cascade is None:
            print("Warning: Face cascade classifier not available")
            return jsonify({
                'stress_level': 'Face Detection Unavailable',
                'status': 'warning'
            })
        
        # Analyze stress level
        stress_level = analyze_facial_stress(cv_image)
        
        # Create a debug image with detections and label for troubleshooting
        try:
            global last_debug_image
            disp = cv_image.copy()
            gray_for_debug = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            # run detection to draw boxes
            faces = []
            try:
                faces = face_cascade.detectMultiScale(gray_for_debug, 1.2, 4, minSize=(30, 30))
            except Exception as _e:
                faces = []

            for (x, y, w, h) in faces:
                cv2.rectangle(disp, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # put label on top-left
            try:
                cv2.putText(disp, str(stress_level), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            except Exception:
                pass

            ret, jpeg = cv2.imencode('.jpg', disp)
            if ret:
                last_debug_image = jpeg.tobytes()
        except Exception as e:
            print(f"Failed to create debug image: {e}")
        
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
        print(f"Error analyzing frame: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to analyze frame',
            'details': str(e)
        }), 500


@app.route('/analyze_frame_blob', methods=['POST'])
def analyze_frame_blob():
    """Analyze uploaded image file (multipart/form-data) for stress detection"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']
        session_id = request.form.get('session_id', 'default')

        data = file.read()
        if not data:
            return jsonify({'error': 'Empty file received'}), 400

        # Decode image from bytes
        try:
            nparr = np.frombuffer(data, np.uint8)
            cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if cv_image is None or cv_image.size == 0:
                return jsonify({'error': 'Invalid image data'}), 400

            # Check if face detection is available
            if face_cascade is None:
                print("Warning: Face cascade classifier not available")
                return jsonify({
                    'stress_level': 'Face Detection Unavailable',
                    'status': 'warning'
                })

            # Analyze stress level
            stress_level = analyze_facial_stress(cv_image)

            # Create debug image
            try:
                global last_debug_image
                disp = cv_image.copy()
                gray_for_debug = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
                faces = []
                try:
                    faces = face_cascade.detectMultiScale(gray_for_debug, 1.2, 4, minSize=(30, 30))
                except Exception:
                    faces = []
                for (x, y, w, h) in faces:
                    cv2.rectangle(disp, (x, y), (x + w, y + h), (0, 255, 0), 2)
                try:
                    cv2.putText(disp, str(stress_level), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                except Exception:
                    pass
                ret, jpeg = cv2.imencode('.jpg', disp)
                if ret:
                    last_debug_image = jpeg.tobytes()
            except Exception as e:
                print(f"Failed to create debug image (blob): {e}")

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
            print(f"Blob decode error: {e}")
            return jsonify({'error': f'Image decode error: {e}'}), 400

    except Exception as e:
        print(f"Error in analyze_frame_blob: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to analyze frame blob', 'details': str(e)}), 500


@app.route('/debug_frame')
def debug_frame():
    """Return the last processed debug image (JPEG) for inspection."""
    global last_debug_image
    try:
        if last_debug_image:
            return Response(last_debug_image, mimetype='image/jpeg')
        else:
            return jsonify({'error': 'No debug image available'}), 404
    except Exception as e:
        print(f"Error returning debug image: {e}")
        return jsonify({'error': 'Failed to return debug image', 'details': str(e)}), 500

def analyze_facial_stress(frame):
    """Analyze facial features for stress indicators"""
    if face_cascade is None:
        print("Face cascade classifier not initialized")
        return 'Unknown'
    
    try:
        # Ensure frame is not empty
        if frame is None or frame.size == 0:
            print("Empty frame received")
            return 'Invalid Frame'
            
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Enhance contrast using histogram equalization
        gray = cv2.equalizeHist(gray)
        
        # Try different scale factors for face detection
        scale_factors = [1.1, 1.2, 1.3]
        min_neighbors_options = [3, 4, 5]
        
        faces = None
        for scale in scale_factors:
            for min_neighbors in min_neighbors_options:
                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=scale,
                    minNeighbors=min_neighbors,
                    minSize=(30, 30),
                    flags=cv2.CASCADE_SCALE_IMAGE
                )
                if len(faces) > 0:
                    print(f"Face detected with scale={scale}, minNeighbors={min_neighbors}")
                    break
            if len(faces) > 0:
                break
        
        if len(faces) == 0:
            print("No faces detected in frame")
            return 'No Face Detected'
            
        # Use the largest face detected
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        (x, y, w, h) = largest_face
        face_roi = gray[y:y+h, x:x+w]
        
        # Calculate facial metrics for stress detection
        # Get face dimensions
        face_height, face_width = face_roi.shape
        face_area = face_height * face_width
        
        # Enhance face region contrast
        face_roi = cv2.equalizeHist(face_roi)
        
        # Define regions of interest with proper bounds checking
        eye_y1 = int(face_height * 0.2)
        eye_y2 = int(face_height * 0.5)
        mouth_y1 = int(face_height * 0.6)
        mouth_y2 = int(face_height * 0.8)
        
        # Ensure we don't exceed bounds
        eye_y2 = min(eye_y2, face_height)
        mouth_y2 = min(mouth_y2, face_height)
        
        # Extract and analyze regions
        eye_region = face_roi[eye_y1:eye_y2, :]
        eye_intensity = np.mean(eye_region) if eye_region.size > 0 else 0
        
        mouth_region = face_roi[mouth_y1:mouth_y2, :]
        mouth_intensity = np.mean(mouth_region) if mouth_region.size > 0 else 0
        
        print(f"Face metrics - Eye intensity: {eye_intensity:.2f}, Mouth intensity: {mouth_intensity:.2f}")
        
        # Adaptive thresholds based on overall face brightness
        face_mean = np.mean(face_roi)
        eye_threshold = face_mean * 0.8
        mouth_threshold = face_mean * 0.9
        
        # Calculate more detailed metrics
        eye_variance = np.std(eye_region) if eye_region.size > 0 else 0
        mouth_variance = np.std(mouth_region) if mouth_region.size > 0 else 0
        
        # Calculate dynamic thresholds
        eye_dynamic_threshold = face_mean * 0.85
        mouth_dynamic_threshold = face_mean * 0.95
        variance_threshold = face_mean * 0.2
        
        print(f"Analysis metrics - Eye var: {eye_variance:.2f}, Mouth var: {mouth_variance:.2f}, Face mean: {face_mean:.2f}")
        
        # Compute a few simple scores for different emotional cues
        scores = {
            'happy': 0.0,
            'sad': 0.0,
            'tired': 0.0,
            'angry': 0.0,
            'nervous': 0.0,
            'stressed': 0.0,
            'calm': 0.0,
            'chill': 0.0,
            'focused': 0.0
        }

        # Bright mouth & high mouth variance -> smile / happy
        if mouth_intensity > face_mean * 1.02 and mouth_variance > variance_threshold:
            scores['happy'] += 2.0

        # Low mouth and low eye intensity -> sad/tired
        if mouth_intensity < face_mean * 0.85 and eye_intensity < face_mean * 0.9:
            scores['sad'] += 1.5
            scores['tired'] += 1.5

        # High eye variance (fidgeting) + quick mouth changes -> nervous
        if eye_variance > variance_threshold and mouth_variance > variance_threshold:
            scores['nervous'] += 2.0

        # High eye variance + low mouth -> stressed/angry
        if eye_variance > variance_threshold and mouth_intensity < face_mean * 0.9:
            scores['stressed'] += 2.0
            scores['angry'] += 1.0

        # Very low variance and steady mid-range intensity -> calm/chill/focused
        if eye_variance < variance_threshold * 0.4 and mouth_variance < variance_threshold * 0.4:
            scores['calm'] += 1.5
            scores['chill'] += 1.0
            scores['focused'] += 1.0

        # Focused: steady gaze but mouth not smiling
        if eye_variance < variance_threshold * 0.5 and mouth_intensity < face_mean * 1.0:
            scores['focused'] += 1.5

        # Tired: low eye intensity (droopy eyelids) and low variance
        if eye_intensity < face_mean * 0.8 and eye_variance < variance_threshold * 0.6:
            scores['tired'] += 2.0

        # Angry: low mouth intensity (tight lips) and more pronounced eyes
        if mouth_intensity < face_mean * 0.88 and eye_intensity > face_mean * 1.05:
            scores['angry'] += 2.0

        # Normalize and pick best; handle ties by a priority list
        best_score = max(scores.values()) if scores else 0.0
        candidates = [k for k, v in scores.items() if v == best_score and v > 0]

        priority = ['stressed', 'angry', 'nervous', 'tired', 'sad', 'focused', 'calm', 'chill', 'happy']
        best_label = 'Normal'
        if candidates:
            # pick highest priority candidate
            for p in priority:
                if p in candidates:
                    best_label = p.capitalize()
                    break
            else:
                best_label = candidates[0].capitalize()

        # If overall face brightness very low, prefer Tired/Sad when applicable
        if face_mean < 50:
            if scores.get('tired', 0) >= 1.0:
                best_label = 'Tired'
            elif scores.get('sad', 0) >= 1.0:
                best_label = 'Sad'

        print(f"Emotion scores: {scores}, chosen: {best_label}")
        return best_label
        
    except Exception as e:
        print(f"Error in stress analysis: {e}")
        return 'Unknown'

@app.route('/results/<session_id>')
def results(session_id):
    """Display results page"""
    if session_id not in typing_sessions:
        return "Session not found", 404
    
    session_data = typing_sessions[session_id]
    # Build stress summary counts for this session (if any)
    session_stress = stress_data.get(session_id, [])
    stress_counts = Counter()
    for item in session_stress:
        label = item.get('stress_level', 'Unknown')
        stress_counts[label] += 1

    # Convert Counter to an ordered dict-like list for template
    stress_summary = dict(stress_counts)

    return render_template('results.html', session=session_data, stress_summary=stress_summary)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)