import pytest
import numpy as np
from face_analyzer import FaceAnalyzer, EmotionLabel, FacialMetrics

@pytest.fixture
def analyzer():
    """Create a FaceAnalyzer instance for testing"""
    return FaceAnalyzer()

def test_emotion_scoring(analyzer):
    """Test emotion scoring logic with simulated metrics"""
    metrics = FacialMetrics(
        eye_intensity=100.0,
        mouth_intensity=120.0,
        eye_variance=20.0,
        mouth_variance=25.0,
        face_mean=100.0
    )
    
    scores = analyzer._compute_emotion_scores(metrics)
    assert isinstance(scores, dict)
    assert all(isinstance(v, float) for v in scores.values())
    
    # Test happy detection (bright mouth, high variance)
    metrics = FacialMetrics(
        eye_intensity=100.0,
        mouth_intensity=105.0,  # > face_mean * 1.02
        eye_variance=10.0,
        mouth_variance=25.0,    # > variance_threshold
        face_mean=100.0
    )
    scores = analyzer._compute_emotion_scores(metrics)
    assert scores[EmotionLabel.HAPPY] > 0

def test_emotion_selection(analyzer):
    """Test emotion selection logic"""
    # Equal scores
    scores = {emotion: 1.0 for emotion in EmotionLabel}
    emotion = analyzer._select_emotion(scores, 100.0)
    assert isinstance(emotion, EmotionLabel)
    
    # No scores
    scores = {emotion: 0.0 for emotion in EmotionLabel}
    emotion = analyzer._select_emotion(scores, 100.0)
    assert emotion == EmotionLabel.NORMAL
    
    # Test dark face override
    scores = {
        EmotionLabel.HAPPY: 2.0,
        EmotionLabel.TIRED: 1.0,
        EmotionLabel.SAD: 1.0
    }
    emotion = analyzer._select_emotion(scores, 40.0)  # Dark face
    assert emotion in [EmotionLabel.TIRED, EmotionLabel.SAD]

def test_metrics_computation(analyzer):
    """Test facial metrics computation"""
    # Create dummy face ROI (100x100 grayscale)
    face_roi = np.ones((100, 100), dtype=np.uint8) * 128
    
    # Add simulated features
    # Eyes region (darker)
    face_roi[20:50, :] = 100
    # Mouth region (brighter)
    face_roi[60:80, :] = 150
    
    metrics = analyzer.compute_metrics(face_roi)
    assert isinstance(metrics, FacialMetrics)
    assert 90 < metrics.eye_intensity < 110  # ~100
    assert 140 < metrics.mouth_intensity < 160  # ~150
    assert metrics.face_mean > 0