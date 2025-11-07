from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np
import time
from enum import Enum

class EmotionLabel(str, Enum):
    HAPPY = 'Happy'
    SAD = 'Sad'
    TIRED = 'Tired'
    ANGRY = 'Angry'
    NERVOUS = 'Nervous'
    STRESSED = 'Stressed'
    CALM = 'Calm'
    CHILL = 'Chill'
    FOCUSED = 'Focused'
    NORMAL = 'Normal'
    UNKNOWN = 'Unknown'

@dataclass
class FacialMetrics:
    eye_intensity: float
    mouth_intensity: float
    eye_variance: float
    mouth_variance: float
    face_mean: float

@dataclass
class StressSample:
    timestamp: float
    stress_level: str

@dataclass
class TypingSession:
    wpm: int
    accuracy: float
    typing_time: float
    stress_level: str
    timestamp: float
    progress: List[int]

class FaceAnalyzer:
    def __init__(self, cascade_path: str = None):
        """Initialize face analyzer with optional cascade path"""
        self.face_cascade = None
        self.last_debug_image = None
        self.initialize_cascade(cascade_path)

    def initialize_cascade(self, cascade_path: str = None) -> bool:
        """Initialize OpenCV cascade classifier"""
        try:
            if not cascade_path:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                print("Error: Failed to load cascade classifier")
                return False
            return True
        except Exception as e:
            print(f"Error initializing cascade: {e}")
            return False

    def detect_face(self, gray: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """Detect the largest face in grayscale image"""
        if not self.face_cascade:
            return None

        faces = []
        for scale in [1.1, 1.2, 1.3]:
            for min_neighbors in [3, 4, 5]:
                try:
                    detected = self.face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=scale,
                        minNeighbors=min_neighbors,
                        minSize=(30, 30),
                        flags=cv2.CASCADE_SCALE_IMAGE
                    )
                    if len(detected):
                        faces.extend(detected)
                except Exception:
                    continue

        if not faces:
            return None

        # Return largest face
        return max(faces, key=lambda f: f[2] * f[3])

    def compute_metrics(self, face_roi: np.ndarray) -> FacialMetrics:
        """Compute facial region metrics"""
        face_height, face_width = face_roi.shape
        
        # Define and validate regions
        eye_y1 = int(face_height * 0.2)
        eye_y2 = min(int(face_height * 0.5), face_height)
        mouth_y1 = int(face_height * 0.6)
        mouth_y2 = min(int(face_height * 0.8), face_height)
        
        # Extract regions and compute metrics
        eye_region = face_roi[eye_y1:eye_y2, :]
        mouth_region = face_roi[mouth_y1:mouth_y2, :]
        
        metrics = FacialMetrics(
            eye_intensity=float(np.mean(eye_region)) if eye_region.size > 0 else 0,
            mouth_intensity=float(np.mean(mouth_region)) if mouth_region.size > 0 else 0,
            eye_variance=float(np.std(eye_region)) if eye_region.size > 0 else 0,
            mouth_variance=float(np.std(mouth_region)) if mouth_region.size > 0 else 0,
            face_mean=float(np.mean(face_roi))
        )
        
        return metrics

    def analyze_stress(self, frame: np.ndarray) -> Tuple[EmotionLabel, Optional[bytes]]:
        """Analyze facial stress and return emotion label plus optional debug image"""
        if frame is None or frame.size == 0 or self.face_cascade is None:
            return EmotionLabel.UNKNOWN, None

        try:
            # Convert and enhance
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            
            # Detect face
            face_rect = self.detect_face(gray)
            if not face_rect:
                return EmotionLabel.UNKNOWN, None
            
            x, y, w, h = face_rect
            face_roi = gray[y:y+h, x:x+w]
            
            # Get metrics
            metrics = self.compute_metrics(face_roi)
            
            # Score emotions
            scores = self._compute_emotion_scores(metrics)
            emotion = self._select_emotion(scores, metrics.face_mean)
            
            # Create debug image
            debug_image = self._create_debug_image(frame, face_rect, str(emotion))
            
            return emotion, debug_image
            
        except Exception as e:
            print(f"Error in stress analysis: {e}")
            return EmotionLabel.UNKNOWN, None

    def _compute_emotion_scores(self, metrics: FacialMetrics) -> Dict[str, float]:
        """Compute emotion scores based on facial metrics"""
        variance_threshold = metrics.face_mean * 0.2
        scores = {emotion: 0.0 for emotion in EmotionLabel}
        
        # Happy: bright mouth & high variance
        if metrics.mouth_intensity > metrics.face_mean * 1.02 and metrics.mouth_variance > variance_threshold:
            scores[EmotionLabel.HAPPY] = 2.0
        
        # Sad/Tired: low intensities
        if metrics.mouth_intensity < metrics.face_mean * 0.85 and metrics.eye_intensity < metrics.face_mean * 0.9:
            scores[EmotionLabel.SAD] = 1.5
            scores[EmotionLabel.TIRED] = 1.5
        
        # Nervous: high variances
        if metrics.eye_variance > variance_threshold and metrics.mouth_variance > variance_threshold:
            scores[EmotionLabel.NERVOUS] = 2.0
        
        # Stressed/Angry: high eye variance + low mouth
        if metrics.eye_variance > variance_threshold and metrics.mouth_intensity < metrics.face_mean * 0.9:
            scores[EmotionLabel.STRESSED] = 2.0
            scores[EmotionLabel.ANGRY] = 1.0
        
        # Calm/Chill/Focused: low variances
        if metrics.eye_variance < variance_threshold * 0.4 and metrics.mouth_variance < variance_threshold * 0.4:
            scores[EmotionLabel.CALM] = 1.5
            scores[EmotionLabel.CHILL] = 1.0
            scores[EmotionLabel.FOCUSED] = 1.0
        
        # Focused: steady gaze
        if metrics.eye_variance < variance_threshold * 0.5 and metrics.mouth_intensity < metrics.face_mean:
            scores[EmotionLabel.FOCUSED] += 1.5
        
        # Tired: low eye intensity
        if metrics.eye_intensity < metrics.face_mean * 0.8 and metrics.eye_variance < variance_threshold * 0.6:
            scores[EmotionLabel.TIRED] += 2.0
        
        # Angry: tight lips + pronounced eyes
        if metrics.mouth_intensity < metrics.face_mean * 0.88 and metrics.eye_intensity > metrics.face_mean * 1.05:
            scores[EmotionLabel.ANGRY] += 2.0
            
        return scores

    def _select_emotion(self, scores: Dict[str, float], face_mean: float) -> EmotionLabel:
        """Select final emotion based on scores and face brightness"""
        best_score = max(scores.values())
        if best_score <= 0:
            return EmotionLabel.NORMAL
            
        candidates = [k for k, v in scores.items() if v == best_score]
        
        # Priority order for tie-breaking
        priority = [
            EmotionLabel.STRESSED,
            EmotionLabel.ANGRY,
            EmotionLabel.NERVOUS,
            EmotionLabel.TIRED,
            EmotionLabel.SAD,
            EmotionLabel.FOCUSED,
            EmotionLabel.CALM,
            EmotionLabel.CHILL,
            EmotionLabel.HAPPY
        ]
        
        # Pick highest priority candidate
        for emotion in priority:
            if emotion in candidates:
                # Override with Tired/Sad for dark faces
                if face_mean < 50:
                    if scores[EmotionLabel.TIRED] >= 1.0:
                        return EmotionLabel.TIRED
                    if scores[EmotionLabel.SAD] >= 1.0:
                        return EmotionLabel.SAD
                return emotion
                
        return EmotionLabel.NORMAL

    def _create_debug_image(self, frame: np.ndarray, face_rect: Tuple[int, int, int, int], label: str) -> Optional[bytes]:
        """Create debug image with face rectangle and label"""
        try:
            disp = frame.copy()
            x, y, w, h = face_rect
            cv2.rectangle(disp, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(disp, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            
            ret, jpeg = cv2.imencode('.jpg', disp)
            if ret:
                return jpeg.tobytes()
        except Exception as e:
            print(f"Debug image creation failed: {e}")
        return None