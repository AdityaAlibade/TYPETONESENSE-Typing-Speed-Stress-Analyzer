import pytest
from app import app
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """Test home page renders correctly"""
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'TypeToneSense' in rv.data
    assert b'Start Test' in rv.data

def test_test_page(client):
    """Test typing test page renders correctly"""
    rv = client.get('/test')
    assert rv.status_code == 200
    assert b'Typing Speed & Stress Analyzer' in rv.data
    assert b'Start Test' in rv.data
    assert b'typing-input' in rv.data

def test_about_page(client):
    """Test about page renders correctly"""
    rv = client.get('/about')
    assert rv.status_code == 200
    assert b'Our Team' in rv.data
    assert b'Alibade Aditya' in rv.data

def test_contact_page(client):
    """Test contact page renders correctly"""
    rv = client.get('/contact')
    assert rv.status_code == 200
    assert b'Contact Us' in rv.data
    assert b'alibadeaditya@gmail.com' in rv.data

def test_get_paragraph(client):
    """Test paragraph endpoint"""
    rv = client.get('/get_paragraph')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert 'paragraph' in data
    assert len(data['paragraph']) > 0

def test_submit_results(client):
    """Test results submission"""
    test_data = {
        'wpm': 60,
        'accuracy': 95,
        'typing_time': 60,
        'session_id': 'test_session',
        'progress': [30, 40, 50, 55, 60]
    }
    rv = client.post('/submit_results', 
                    json=test_data,
                    content_type='application/json')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert 'session_id' in data

def test_results_page(client):
    """Test results page with submitted data"""
    # First submit test data
    test_data = {
        'wpm': 60,
        'accuracy': 95,
        'typing_time': 60,
        'session_id': 'test_session_results',
        'progress': [30, 40, 50, 55, 60]
    }
    client.post('/submit_results', 
                json=test_data,
                content_type='application/json')
    
    # Then check results page
    rv = client.get('/results/test_session_results')
    assert rv.status_code == 200
    assert b'60' in rv.data  # WPM value
    assert b'95%' in rv.data  # Accuracy value