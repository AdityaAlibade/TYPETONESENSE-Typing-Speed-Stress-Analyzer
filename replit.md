# Typing Speed & Stress Analyzer

## Overview

A web-based typing speed test application that analyzes user performance and stress levels during typing exercises. The application provides a clean interface for users to practice typing with various sample paragraphs and tracks their performance metrics. Built with Flask for the backend and vanilla HTML/CSS/JavaScript for the frontend, this project demonstrates a simple yet effective approach to creating interactive typing assessment tools.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Single Page Application**: Uses vanilla HTML, CSS, and JavaScript without complex frameworks
- **Grid-based Layout**: Responsive design using CSS Grid for main content areas
- **Component Structure**: Separate templates for main typing interface (`index.html`) and results display (`results.html`)
- **Real-time Interaction**: Client-side JavaScript handles typing events, timing, and progress tracking

### Backend Architecture
- **Flask Web Framework**: Lightweight Python web server handling HTTP requests
- **RESTful API Design**: JSON endpoints for paragraph retrieval and data exchange
- **Session Management**: Server-side session handling with configurable secret key
- **In-Memory Data Storage**: Global dictionaries for storing typing sessions and stress data
- **Modular Route Structure**: Separate routes for main interface and API endpoints

### Computer Vision Integration
- **OpenCV Integration**: Face detection capabilities using Haar Cascade classifiers
- **Image Processing Pipeline**: Base64 image decoding and PIL integration for image manipulation
- **Stress Detection Framework**: Foundation for analyzing facial expressions during typing sessions
- **Fallback Handling**: Graceful degradation when computer vision components are unavailable

### Data Management
- **Session Tracking**: Individual typing session data storage and retrieval
- **Performance Metrics**: Real-time calculation of typing speed, accuracy, and completion rates
- **Sample Content Management**: Predefined paragraph collection covering diverse topics for typing practice

## External Dependencies

### Python Libraries
- **Flask**: Web application framework for HTTP handling and templating
- **OpenCV (cv2)**: Computer vision library for face detection and image processing
- **NumPy**: Numerical computing for image array manipulation
- **Pillow (PIL)**: Image processing library for format conversion and manipulation

### Frontend Technologies
- **Vanilla JavaScript**: Client-side interaction handling without external frameworks
- **CSS Grid**: Modern layout system for responsive design
- **HTML5**: Semantic markup for accessibility and structure

### System Resources
- **Haar Cascade Classifiers**: Pre-trained face detection models from OpenCV
- **Environment Variables**: Configuration through system environment for security
- **File System**: Template rendering and static asset serving

### Potential Integration Points
- **Database Systems**: Ready for integration with persistent storage solutions
- **Authentication Services**: Framework prepared for user management systems
- **Analytics Platforms**: Data structure supports external analytics integration
- **Real-time Communication**: Architecture supports WebSocket integration for live features