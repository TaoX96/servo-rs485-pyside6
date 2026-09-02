#!/usr/bin/env python3
"""
Raspberry Pi Comprehensive Monitoring Service
Integrated features:
1. 1-Wire temperature sensor data acquisition
2. Real-time video streaming
3. Static image capture
4. Video recording
5. Web control interface
6. LabVIEW integration API endpoints
7. PC file transfer functionality
8. Enhanced LabVIEW control with duration parameter
9. Custom filename prefixes and new timestamp format
"""

import io
import time
import threading
import logging
import glob
import os
import cv2
import numpy as np
import shutil
import re
from datetime import datetime
from flask import Flask, Response, request, jsonify, render_template_string, send_file
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global variables
camera = None
is_recording = False
recording_thread = None
current_stream_clients = 0
frame_buffer = None
frame_lock = threading.Lock()
current_temperature = None
temperature_lock = threading.Lock()

# LabVIEW control parameters
labview_recording_duration = 30  # Default duration in seconds
labview_lock = threading.Lock()

# Custom filename prefix
custom_filename_prefix = ""
filename_prefix_lock = threading.Lock()

# Create storage directories
os.makedirs("recordings", exist_ok=True)
os.makedirs("images", exist_ok=True)
os.makedirs("pc_transfer", exist_ok=True)

def get_timestamp():
    """Get current timestamp in HH-MM-SS_DD-MM-YYYY format"""
    return datetime.now().strftime("%H-%M-%S_%d-%m-%Y")

def get_filename(prefix, base_name, extension):
    """Generate filename with custom prefix and timestamp"""
    with filename_prefix_lock:
        custom_prefix = custom_filename_prefix
    
    timestamp = get_timestamp()
    
    if custom_prefix:
        if prefix:
            filename = f"{custom_prefix}_{prefix}_{timestamp}.{extension}"
        else:
            filename = f"{custom_prefix}_{timestamp}.{extension}"
    else:
        if prefix:
            filename = f"{prefix}_{timestamp}.{extension}"
        else:
            filename = f"{timestamp}.{extension}"
    
    return filename

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raspberry Pi Comprehensive Monitoring System</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            text-align: center;
            color: #2c3e50;
        }
        .dashboard {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 20px;
        }
        .video-container {
            flex: 2;
            min-width: 300px;
        }
        .status-panel {
            flex: 1;
            min-width: 250px;
            background: #f9f9f9;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        }
        .controls {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 20px 0;
            justify-content: center;
        }
        button {
            padding: 10px 15px;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        button:hover {
            background: #2980b9;
        }
        #recordBtn.recording {
            background: #e74c3c;
        }
        #recordBtn.recording:hover {
            background: #c0392b;
        }
        .temp-display {
            font-size: 24px;
            font-weight: bold;
            color: #e67e22;
            margin: 10px 0;
        }
        .status-item {
            margin: 8px 0;
            display: flex;
            justify-content: space-between;
        }
        .status-label {
            font-weight: bold;
        }
        video, img {
            width: 100%;
            border-radius: 6px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .history {
            margin-top: 20px;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 6px;
        }
        .history h3 {
            margin-top: 0;
        }
        .file-list {
            max-height: 200px;
            overflow-y: auto;
        }
        .file-item {
            padding: 5px;
            border-bottom: 1px solid #eee;
        }
        .file-item:last-child {
            border-bottom: none;
        }
        .pc-transfer {
            margin-top: 20px;
            padding: 15px;
            background: #f0f8ff;
            border-radius: 6px;
            border-left: 4px solid #27ae60;
        }
        .transfer-controls {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 10px 0;
        }
        .transfer-btn {
            background: #27ae60;
        }
        .transfer-btn:hover {
            background: #219653;
        }
        .filename-controls {
            margin-top: 20px;
            padding: 15px;
            background: #fff8e1;
            border-radius: 6px;
            border-left: 4px solid #ffa000;
        }
        .filename-input {
            display: flex;
            gap: 10px;
            align-items: center;
            margin: 10px 0;
        }
        .filename-input input {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            flex: 1;
        }
        .prefix-btn {
            background: #ffa000;
        }
        .prefix-btn:hover {
            background: #ff8f00;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Raspberry Pi Comprehensive Monitoring System</h1>
        
        <div class="dashboard">
            <div class="video-container">
                <h2>Live Monitoring</h2>
                <img src="/video_feed" alt="Live Video Stream">
            </div>
            
            <div class="status-panel">
                <h2>System Status</h2>
                <div class="temp-display">
                    Temperature: <span id="temperature">--</span> °C
                </div>
                
                <div class="status-item">
                    <span class="status-label">Camera Status:</span>
                    <span id="cameraStatus">{% if camera_ready %}Ready{% else %}Not Ready{% endif %}</span>
                </div>
                
                <div class="status-item">
                    <span class="status-label">Recording Status:</span>
                    <span id="recordingStatus">{% if is_recording %}Active{% else %}Inactive{% endif %}</span>
                </div>
                
                <div class="status-item">
                    <span class="status-label">Client Count:</span>
                    <span id="clientCount">{{ current_stream_clients }}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Filename Prefix:</span>
                    <span id="filenamePrefix">{{ filename_prefix }}</span>
                </div>
            </div>
        </div>

        <!-- Filename Prefix Control -->
        <div class="filename-controls">
            <h2>Filename Settings</h2>
            <div class="filename-input">
                <input type="text" id="filenamePrefixInput" placeholder="Enter custom filename prefix">
                <button class="prefix-btn" onclick="setFilenamePrefix()">Set Prefix</button>
                <button class="prefix-btn" onclick="clearFilenamePrefix()">Clear Prefix</button>
            </div>
            <div>
                <small>Current timestamp format: HH-MM-SS_DD-MM-YYYY</small>
            </div>
            <div id="prefixStatus" style="margin-top: 10px; font-weight: bold;"></div>
        </div>
        
        <div class="controls">
            <button onclick="captureImage()">Capture Image</button>
            <button id="recordBtn" onclick="toggleRecording()" class="{% if is_recording %}recording{% endif %}">
                {% if is_recording %}Stop Recording{% else %}Start Recording{% endif %}
            </button>
            <div>
                <label>Recording Duration(seconds): </label>
                <input type="number" id="duration" value="30" min="1" style="width: 60px;">
            </div>
            <button onclick="refreshTemperature()">Refresh Temperature</button>
        </div>

        <!-- PC File Transfer Control Area -->
        <div class="pc-transfer">
            <h2>PC File Transfer</h2>
            <div class="transfer-controls">
                <button class="transfer-btn" onclick="transferLatestImage()">Transfer Latest Image to PC</button>
                <button class="transfer-btn" onclick="transferLatestVideo()">Transfer Latest Video to PC</button>
                <button class="transfer-btn" onclick="transferAllImages()">Transfer All Images to PC</button>
                <button class="transfer-btn" onclick="transferAllVideos()">Transfer All Videos to PC</button>
            </div>
            <div>
                <label>Custom Video Duration (seconds): </label>
                <input type="number" id="customDuration" value="10" min="1" max="300" style="width: 60px;">
                <button class="transfer-btn" onclick="captureAndTransferVideo()">Record & Transfer Custom Video</button>
            </div>
            <div id="transferStatus" style="margin-top: 10px; font-weight: bold;"></div>
        </div>
        
        <div class="history">
            <h3>File History</h3>
            <div class="file-list">
                <div class="file-item">
                    <strong>Image Files:</strong>
                    <ul id="imageFiles">
                        {% for file in image_files %}
                        <li>{{ file }}</li>
                        {% endfor %}
                    </ul>
                </div>
                <div class="file-item">
                    <strong>Video Files:</strong>
                    <ul id="videoFiles">
                        {% for file in video_files %}
                        <li>{{ file }}</li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Update temperature display
        function updateTemperature() {
            fetch('/api/temperature')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('temperature').textContent = data.temperature.toFixed(2);
                })
                .catch(error => {
                    console.error('Failed to get temperature:', error);
                });
        }
        
        // Refresh temperature
        function refreshTemperature() {
            updateTemperature();
        }
        
        // Capture image
        function captureImage() {
            fetch('/api/capture')
                .then(response => response.json())
                .then(data => {
                    alert('Image saved: ' + data.filename);
                    // Refresh file list
                    fetchFileList();
                })
                .catch(error => {
                    console.error('Image capture failed:', error);
                    alert('Image capture failed: ' + error);
                });
        }
        
        // Toggle recording status
        function toggleRecording() {
            const btn = document.getElementById('recordBtn');
            const duration = document.getElementById('duration').value;
            
            if (btn.textContent === 'Start Recording') {
                fetch('/api/start_recording?duration=' + duration)
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'recording') {
                            btn.textContent = 'Stop Recording';
                            btn.classList.add('recording');
                            document.getElementById('recordingStatus').textContent = 'Active';
                        }
                    })
                    .catch(error => {
                        console.error('Start recording failed:', error);
                        alert('Start recording failed: ' + error);
                    });
            } else {
                fetch('/api/stop_recording')
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'stopped') {
                            btn.textContent = 'Start Recording';
                            btn.classList.remove('recording');
                            document.getElementById('recordingStatus').textContent = 'Inactive';
                            // Refresh file list
                            fetchFileList();
                        }
                    })
                    .catch(error => {
                        console.error('Stop recording failed:', error);
                        alert('Stop recording failed: ' + error);
                    });
            }
        }
        
        // Get file list
        function fetchFileList() {
            fetch('/api/files')
                .then(response => response.json())
                .then(data => {
                    // Update image file list
                    const imageList = document.getElementById('imageFiles');
                    imageList.innerHTML = '';
                    data.images.forEach(file => {
                        const li = document.createElement('li');
                        li.textContent = file;
                        imageList.appendChild(li);
                    });
                    
                    // Update video file list
                    const videoList = document.getElementById('videoFiles');
                    videoList.innerHTML = '';
                    data.videos.forEach(file => {
                        const li = document.createElement('li');
                        li.textContent = file;
                        videoList.appendChild(li);
                    });
                })
                .catch(error => {
                    console.error('Failed to get file list:', error);
                });
        }

        // Filename prefix functions
        function setFilenamePrefix() {
            const prefixInput = document.getElementById('filenamePrefixInput');
            const prefix = prefixInput.value.trim();
            
            if (prefix) {
                fetch('/api/set_filename_prefix?prefix=' + encodeURIComponent(prefix))
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            document.getElementById('filenamePrefix').textContent = prefix;
                            document.getElementById('prefixStatus').textContent = 'Prefix set successfully: ' + prefix;
                            document.getElementById('prefixStatus').style.color = 'green';
                            prefixInput.value = '';
                        } else {
                            document.getElementById('prefixStatus').textContent = 'Failed to set prefix: ' + data.message;
                            document.getElementById('prefixStatus').style.color = 'red';
                        }
                    })
                    .catch(error => {
                        console.error('Set prefix failed:', error);
                        document.getElementById('prefixStatus').textContent = 'Failed to set prefix: ' + error;
                        document.getElementById('prefixStatus').style.color = 'red';
                    });
            } else {
                document.getElementById('prefixStatus').textContent = 'Please enter a prefix';
                document.getElementById('prefixStatus').style.color = 'red';
            }
        }

        function clearFilenamePrefix() {
            fetch('/api/clear_filename_prefix')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        document.getElementById('filenamePrefix').textContent = '';
                        document.getElementById('prefixStatus').textContent = 'Prefix cleared successfully';
                        document.getElementById('prefixStatus').style.color = 'green';
                        document.getElementById('filenamePrefixInput').value = '';
                    } else {
                        document.getElementById('prefixStatus').textContent = 'Failed to clear prefix: ' + data.message;
                        document.getElementById('prefixStatus').style.color = 'red';
                    }
                })
                .catch(error => {
                    console.error('Clear prefix failed:', error);
                    document.getElementById('prefixStatus').textContent = 'Failed to clear prefix: ' + error;
                    document.getElementById('prefixStatus').style.color = 'red';
                });
        }

        // PC Transfer related functions
        function updateTransferStatus(message, isError = false) {
            const statusElement = document.getElementById('transferStatus');
            statusElement.textContent = message;
            statusElement.style.color = isError ? 'red' : 'green';
        }

        function transferLatestImage() {
            updateTransferStatus('Transferring latest image...');
            fetch('/api/transfer/latest_image')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        updateTransferStatus('Image transferred successfully: ' + data.filename);
                        // Provide download link
                        const downloadLink = document.createElement('a');
                        downloadLink.href = '/api/download/' + data.filename;
                        downloadLink.download = data.filename;
                        downloadLink.click();
                    } else {
                        updateTransferStatus('Transfer failed: ' + data.message, true);
                    }
                })
                .catch(error => {
                    console.error('Transfer failed:', error);
                    updateTransferStatus('Transfer failed: ' + error, true);
                });
        }

        function transferLatestVideo() {
            updateTransferStatus('Transferring latest video...');
            fetch('/api/transfer/latest_video')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        updateTransferStatus('Video transferred successfully: ' + data.filename);
                        // Provide download link
                        const downloadLink = document.createElement('a');
                        downloadLink.href = '/api/download/' + data.filename;
                        downloadLink.download = data.filename;
                        downloadLink.click();
                    } else {
                        updateTransferStatus('Transfer failed: ' + data.message, true);
                    }
                })
                .catch(error => {
                    console.error('Transfer failed:', error);
                    updateTransferStatus('Transfer failed: ' + error, true);
                });
        }

        function transferAllImages() {
            updateTransferStatus('Transferring all images...');
            fetch('/api/transfer/all_images')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        updateTransferStatus('All images transferred successfully. Downloading archive...');
                        // Provide download link
                        const downloadLink = document.createElement('a');
                        downloadLink.href = '/api/download/' + data.filename;
                        downloadLink.download = data.filename;
                        downloadLink.click();
                    } else {
                        updateTransferStatus('Transfer failed: ' + data.message, true);
                    }
                })
                .catch(error => {
                    console.error('Transfer failed:', error);
                    updateTransferStatus('Transfer failed: ' + error, true);
                });
        }

        function transferAllVideos() {
            updateTransferStatus('Transferring all videos...');
            fetch('/api/transfer/all_videos')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        updateTransferStatus('All videos transferred successfully. Downloading archive...');
                        // Provide download link
                        const downloadLink = document.createElement('a');
                        downloadLink.href = '/api/download/' + data.filename;
                        downloadLink.download = data.filename;
                        downloadLink.click();
                    } else {
                        updateTransferStatus('Transfer failed: ' + data.message, true);
                    }
                })
                .catch(error => {
                    console.error('Transfer failed:', error);
                    updateTransferStatus('Transfer failed: ' + error, true);
                });
        }

        function captureAndTransferVideo() {
            const duration = document.getElementById('customDuration').value;
            updateTransferStatus('Recording and transferring video (' + duration + 's)...');
            
            fetch('/api/transfer/capture_video?duration=' + duration)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        updateTransferStatus('Video recorded and transferred successfully: ' + data.filename);
                        // Provide download link
                        const downloadLink = document.createElement('a');
                        downloadLink.href = '/api/download/' + data.filename;
                        downloadLink.download = data.filename;
                        downloadLink.click();
                    } else {
                        updateTransferStatus('Video capture/transfer failed: ' + data.message, true);
                    }
                })
                .catch(error => {
                    console.error('Video capture/transfer failed:', error);
                    updateTransferStatus('Video capture/transfer failed: ' + error, true);
                });
        }
        
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            // Initial temperature update
            updateTemperature();
            
            // Auto-update temperature every 10 seconds
            setInterval(updateTemperature, 10000);
            
            // Update file list every 30 seconds
            setInterval(fetchFileList, 30000);
        });
    </script>
</body>
</html>
"""

def init_camera():
    """Initialize camera"""
    global camera
    try:
        camera = Picamera2()
        
        # Configure video preview
        video_config = camera.create_video_configuration(
            main={"size": (1280, 720), "format": "RGB888"}
        )
        camera.configure(video_config)
        
        # Start camera
        camera.start()
        logger.info("Camera initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Camera initialization failed: {e}")
        return False

def init_temperature_sensor():
    """Initialize temperature sensor"""
    try:
        # Find 1-Wire devices
        base_dir = '/sys/bus/w1/devices/'
        device_folder = glob.glob(base_dir + '28*')[0]
        device_file = device_folder + '/w1_slave'
        
        logger.info(f"Temperature sensor found: {device_folder}")
        return device_file
    except IndexError:
        logger.error("Temperature sensor not found, please check connection and setup")
        return None

def read_temperature(device_file):
    """Read temperature from 1-Wire sensor"""
    try:
        with open(device_file, 'r') as f:
            lines = f.readlines()
        
        # Check data validity
        if lines[0].strip()[-3:] != 'YES':
            return None
        
        # Extract temperature value
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            return temp_c
    except Exception as e:
        logger.error(f"Failed to read temperature: {e}")
    
    return None

def temperature_monitor(device_file):
    """Temperature monitoring thread"""
    global current_temperature
    
    if not device_file:
        logger.error("Temperature sensor not initialized, cannot start monitoring")
        return
    
    while True:
        try:
            temp = read_temperature(device_file)
            if temp is not None:
                with temperature_lock:
                    current_temperature = temp
                logger.debug(f"Current temperature: {temp}°C")
            else:
                logger.warning("Failed to get temperature reading")
        except Exception as e:
            logger.error(f"Temperature monitoring error: {e}")
        
        # Update temperature every 5 seconds
        time.sleep(5)

def generate_frames():
    """Generate MJPEG frame stream"""
    global current_stream_clients, frame_buffer
    
    current_stream_clients += 1
    logger.info(f"New client connected, current clients: {current_stream_clients}")
    
    try:
        while True:
            if frame_buffer is not None:
                # Convert frame to JPEG
                with frame_lock:
                    frame = frame_buffer.copy()
                
                ret, jpeg_buffer = cv2.imencode('.jpg', frame, 
                                               [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret:
                    frame_data = jpeg_buffer.tobytes()
                    
                    # Generate MJPEG stream
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
            
            # Control frame rate
            time.sleep(0.033)  # Approximately 30fps
            
    except GeneratorExit:
        current_stream_clients -= 1
        logger.info(f"Client disconnected, remaining clients: {current_stream_clients}")
    except Exception as e:
        logger.error(f"Video stream generation error: {e}")
        current_stream_clients -= 1

def camera_capture_loop():
    """Camera capture loop - runs in background thread"""
    global frame_buffer
    
    if not camera:
        logger.error("Camera not initialized, cannot start capture loop")
        return
    
    try:
        while True:
            # Capture frame
            frame = camera.capture_array()
            
            # Update frame buffer
            with frame_lock:
                frame_buffer = frame
                
            # Control frame rate
            time.sleep(0.033)  # Approximately 30fps
            
    except Exception as e:
        logger.error(f"Camera capture loop error: {e}")

def recording_worker(filename, duration=None):
    """Recording worker thread"""
    global is_recording, camera
    
    try:
        logger.info(f"Starting recording: {filename}")
        
        # Configure video encoder
        encoder = H264Encoder(bitrate=5000000)  # 5 Mbps
        output = FfmpegOutput(filename)
        
        # Start recording
        camera.start_recording(encoder, output)
        
        # If duration specified, set timer to stop
        if duration:
            start_time = time.time()
            while is_recording and (time.time() - start_time < duration):
                time.sleep(0.1)
        else:
            # Otherwise record until stop signal received
            while is_recording:
                time.sleep(0.1)
                
        camera.stop_recording()
        logger.info(f"Recording completed: {filename}")
        
    except Exception as e:
        logger.error(f"Recording error: {e}")
    finally:
        is_recording = False

def get_file_list():
    """Get stored file list"""
    images = []
    videos = []
    
    try:
        # Get image file list
        if os.path.exists("images"):
            images = sorted(os.listdir("images"), reverse=True)
            images = images[:10]  # Only show recent 10 files
        
        # Get video file list
        if os.path.exists("recordings"):
            videos = sorted(os.listdir("recordings"), reverse=True)
            videos = videos[:10]  # Only show recent 10 files
    except Exception as e:
        logger.error(f"Failed to get file list: {e}")
    
    return images, videos

# PC Transfer function functions
def get_latest_file(directory, extension=None):
    """Get the latest file in the specified directory"""
    try:
        files = []
        for file in os.listdir(directory):
            if extension is None or file.endswith(extension):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    files.append((file, os.path.getmtime(file_path)))
        
        if not files:
            return None
        
        # Sort by modification time, return the latest file
        files.sort(key=lambda x: x[1], reverse=True)
        return files[0][0]
    except Exception as e:
        logger.error(f"Error getting latest file from {directory}: {e}")
        return None

def copy_file_to_pc_transfer(source_path, target_filename):
    """Copy file to PC transfer directory"""
    try:
        pc_transfer_path = os.path.join("pc_transfer", target_filename)
        shutil.copy2(source_path, pc_transfer_path)
        logger.info(f"File copied to PC transfer: {source_path} -> {pc_transfer_path}")
        return pc_transfer_path
    except Exception as e:
        logger.error(f"Error copying file to PC transfer: {e}")
        return None

def create_zip_archive(files, archive_name):
    """Create ZIP archive"""
    try:
        import zipfile
        archive_path = os.path.join("pc_transfer", archive_name)
        
        with zipfile.ZipFile(archive_path, 'w') as zipf:
            for file in files:
                file_path = os.path.join("pc_transfer", file)
                if os.path.exists(file_path):
                    zipf.write(file_path, file)
        
        logger.info(f"ZIP archive created: {archive_path}")
        return archive_path
    except Exception as e:
        logger.error(f"Error creating ZIP archive: {e}")
        return None

# Flask routes
@app.route('/')
def index():
    """Main page"""
    images, videos = get_file_list()
    return render_template_string(HTML_TEMPLATE, 
                                 camera_ready=camera is not None,
                                 is_recording=is_recording,
                                 current_stream_clients=current_stream_clients,
                                 image_files=images,
                                 video_files=videos,
                                 filename_prefix=custom_filename_prefix)

@app.route('/video_feed')
def video_feed():
    """Video stream endpoint"""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

# Filename prefix API endpoints
@app.route('/api/set_filename_prefix')
def api_set_filename_prefix():
    """Set custom filename prefix"""
    global custom_filename_prefix
    prefix = request.args.get('prefix', '').strip()
    
    # Sanitize prefix to remove any invalid characters
    prefix = re.sub(r'[^\w\-_]', '', prefix)
    
    with filename_prefix_lock:
        custom_filename_prefix = prefix
    
    logger.info(f"Filename prefix set to: {prefix}")
    return jsonify({
        "status": "success", 
        "message": f"Filename prefix set to: {prefix}",
        "prefix": prefix
    })

@app.route('/api/clear_filename_prefix')
def api_clear_filename_prefix():
    """Clear custom filename prefix"""
    global custom_filename_prefix
    
    with filename_prefix_lock:
        old_prefix = custom_filename_prefix
        custom_filename_prefix = ""
    
    logger.info(f"Filename prefix cleared (was: {old_prefix})")
    return jsonify({
        "status": "success", 
        "message": "Filename prefix cleared"
    })

# Basic API endpoints
@app.route('/api/temperature')
def api_temperature():
    """Get temperature API"""
    with temperature_lock:
        temp = current_temperature
    
    if temp is None:
        return jsonify({"status": "error", "message": "Unable to get temperature reading"}), 500
    
    return jsonify({"status": "success", "temperature": temp})

@app.route('/api/capture')
def api_capture():
    """Capture still image API"""
    try:
        if not camera:
            return jsonify({"status": "error", "message": "Camera not initialized"}), 500
        
        # Generate filename with custom prefix
        filename = get_filename("capture", "image", "jpg")
        filepath = os.path.join("images", filename)
        
        # Use camera to capture high-resolution image
        camera.capture_file(filepath)
        
        logger.info(f"Image saved: {filename}")
        return jsonify({"status": "success", "filename": filename})
    except Exception as e:
        logger.error(f"Image capture error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/start_recording')
def api_start_recording():
    """Start video recording API"""
    global is_recording, recording_thread
    
    if not camera:
        return jsonify({"status": "error", "message": "Camera not initialized"}), 500
    
    if is_recording:
        return jsonify({"status": "error", "message": "Recording already in progress"}), 400
    
    try:
        duration = request.args.get('duration', type=int, default=0)
        
        # Generate filename with custom prefix
        filename = get_filename("video", "video", "mp4")
        filepath = os.path.join("recordings", filename)
        
        is_recording = True
        recording_thread = threading.Thread(
            target=recording_worker, 
            args=(filepath, duration if duration > 0 else None)
        )
        recording_thread.daemon = True
        recording_thread.start()
        
        logger.info(f"Starting recording: {filename}, Duration: {duration if duration > 0 else 'Unlimited'}")
        return jsonify({
            "status": "success", 
            "filename": filename,
            "duration": duration
        })
    except Exception as e:
        logger.error(f"Start recording error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/stop_recording')
def api_stop_recording():
    """Stop video recording API"""
    global is_recording
    
    if not is_recording:
        return jsonify({"status": "error", "message": "No active recording"}), 400
    
    is_recording = False
    if recording_thread and recording_thread.is_alive():
        recording_thread.join(timeout=5.0)
    
    logger.info("Recording stopped")
    return jsonify({"status": "success", "message": "Recording stopped"})

@app.route('/api/files')
def api_files():
    """Get file list API"""
    images, videos = get_file_list()
    return jsonify({"images": images, "videos": videos})

@app.route('/api/status')
def api_status():
    """Get system status API"""
    return jsonify({
        "camera_initialized": camera is not None,
        "is_recording": is_recording,
        "stream_clients": current_stream_clients,
        "temperature": current_temperature
    })

# LabVIEW Integration API Endpoints
@app.route('/api/camera/start')
def api_camera_start():
    """Start camera - LabVIEW integration"""
    try:
        global camera
        if camera is None:
            success = init_camera()
            if success:
                # Start camera capture thread
                capture_thread = threading.Thread(target=camera_capture_loop)
                capture_thread.daemon = True
                capture_thread.start()
                logger.info("Camera started via API")
                return jsonify({"status": "success", "message": "Camera started"})
            else:
                return jsonify({"status": "error", "message": "Failed to initialize camera"}), 500
        else:
            return jsonify({"status": "success", "message": "Camera already running"})
    except Exception as e:
        logger.error(f"Camera start error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/camera/stop')
def api_camera_stop():
    """Stop camera - LabVIEW integration"""
    try:
        global camera
        if camera:
            camera.stop()
            camera = None
            logger.info("Camera stopped via API")
            return jsonify({"status": "success", "message": "Camera stopped"})
        else:
            return jsonify({"status": "success", "message": "Camera not running"})
    except Exception as e:
        logger.error(f"Camera stop error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/snapshot')
def api_snapshot():
    """Get real-time snapshot - LabVIEW integration"""
    try:
        if not camera or frame_buffer is None:
            return jsonify({"status": "error", "message": "Camera not ready"}), 500
        
        with frame_lock:
            frame = frame_buffer.copy()
        
        # Convert to JPEG
        ret, jpeg_buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ret:
            from base64 import b64encode
            image_b64 = b64encode(jpeg_buffer).decode('utf-8')
            return jsonify({
                "status": "success", 
                "image": image_b64,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({"status": "error", "message": "Image encoding failed"}), 500
            
    except Exception as e:
        logger.error(f"Snapshot error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/snapshot/save')
def api_snapshot_save():
    """Save snapshot and return filename - LabVIEW integration"""
    try:
        # Generate filename with custom prefix
        filename = get_filename("snapshot", "image", "jpg")
        filepath = os.path.join("images", filename)
        
        if not camera:
            return jsonify({"status": "error", "message": "Camera not ready"}), 500
        
        camera.capture_file(filepath)
        
        logger.info(f"Snapshot saved via API: {filename}")
        return jsonify({
            "status": "success", 
            "filename": filename,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Snapshot save error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Enhanced LabVIEW Integration API Endpoints
@app.route('/labview/control', methods=['GET', 'POST'])
def labview_control():
    """
    LabVIEW comprehensive control interface
    GET: Get current status and parameters
    POST: Execute control commands
    """
    global is_recording, recording_thread, labview_recording_duration

    if request.method == 'GET':
        # Return current status and parameters
        with labview_lock:
            duration = labview_recording_duration
        
        with temperature_lock:
            temp = current_temperature
        
        with filename_prefix_lock:
            prefix = custom_filename_prefix
        
        return jsonify({
            "status": "success",
            "camera_initialized": camera is not None,
            "is_recording": is_recording,
            "recording_duration": duration,
            "temperature": temp,
            "stream_clients": current_stream_clients,
            "filename_prefix": prefix
        })
    
    elif request.method == 'POST':
        # Execute control commands
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON data provided"}), 400
        
        command = data.get('command', '')
        parameters = data.get('parameters', {})
        
        try:
            if command == "set_duration":
                duration = parameters.get('duration', 30)
                with labview_lock:
                    labview_recording_duration = max(1, int(duration))
                return jsonify({
                    "status": "success", 
                    "message": f"Recording duration set to {labview_recording_duration} seconds"
                })
            
            elif command == "set_filename_prefix":
                prefix = parameters.get('prefix', '').strip()
                prefix = re.sub(r'[^\w\-_]', '', prefix)
                
                with filename_prefix_lock:
                    custom_filename_prefix = prefix
                
                return jsonify({
                    "status": "success", 
                    "message": f"Filename prefix set to: {prefix}",
                    "prefix": prefix
                })
            
            elif command == "clear_filename_prefix":
                with filename_prefix_lock:
                    custom_filename_prefix = ""
                
                return jsonify({
                    "status": "success", 
                    "message": "Filename prefix cleared"
                })
            
            elif command == "start_recording":
                with labview_lock:
                    duration = labview_recording_duration
                
                if is_recording:
                    return jsonify({"status": "error", "message": "Recording already in progress"}), 400
                
                # Generate filename with custom prefix
                filename = get_filename("labview", "video", "mp4")
                filepath = os.path.join("recordings", filename)
                
                is_recording = True
                recording_thread = threading.Thread(
                    target=recording_worker, 
                    args=(filepath, duration)
                )
                recording_thread.daemon = True
                recording_thread.start()
                
                return jsonify({
                    "status": "success", 
                    "message": f"Recording started for {duration} seconds",
                    "filename": filename,
                    "duration": duration
                })
            
            elif command == "stop_recording":
                if not is_recording:
                    return jsonify({"status": "error", "message": "No active recording"}), 400
                
                is_recording = False
                if recording_thread and recording_thread.is_alive():
                    recording_thread.join(timeout=5.0)
                
                return jsonify({"status": "success", "message": "Recording stopped"})
            
            elif command == "capture_image":
                if not camera:
                    return jsonify({"status": "error", "message": "Camera not initialized"}), 500
                
                # Generate filename with custom prefix
                filename = get_filename("labview", "image", "jpg")
                filepath = os.path.join("images", filename)
                camera.capture_file(filepath)
                
                return jsonify({
                    "status": "success", 
                    "message": "Image captured",
                    "filename": filename
                })
            
            elif command == "get_temperature":
                with temperature_lock:
                    temp = current_temperature
                
                if temp is None:
                    return jsonify({"status": "error", "message": "Temperature not available"}), 500
                
                return jsonify({
                    "status": "success", 
                    "temperature": temp
                })
            
            else:
                return jsonify({"status": "error", "message": f"Unknown command: {command}"}), 400
                
        except Exception as e:
            logger.error(f"LabVIEW control error: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/labview/record_with_duration', methods=['POST'])
def labview_record_with_duration():
    """
    LabVIEW dedicated recording interface - can specify recording duration
    """
    global is_recording, recording_thread

    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON data provided"}), 400
    
    duration = data.get('duration', 30)
    duration = max(1, int(duration))  # Ensure duration is at least 1 second
    
    if is_recording:
        return jsonify({"status": "error", "message": "Recording already in progress"}), 400
    
    try:
        # Generate filename with custom prefix and duration
        filename = get_filename(f"labview_{duration}s", "video", "mp4")
        filepath = os.path.join("recordings", filename)
        
        is_recording = True
        recording_thread = threading.Thread(
            target=recording_worker, 
            args=(filepath, duration)
        )
        recording_thread.daemon = True
        recording_thread.start()
        
        # Wait for recording to complete
        recording_thread.join()
        
        return jsonify({
            "status": "success", 
            "message": f"Recording completed: {duration} seconds",
            "filename": filename,
            "duration": duration
        })
        
    except Exception as e:
        logger.error(f"LabVIEW recording error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/labview/transfer_latest_video', methods=['GET', 'POST'])
def labview_transfer_latest_video():
    """
    LabVIEW dedicated - transfer latest video to PC
    """
    try:
        latest_video = get_latest_file("recordings", ".mp4")
        if not latest_video:
            return jsonify({"status": "error", "message": "No video files found"}), 404
        
        source_path = os.path.join("recordings", latest_video)
        timestamp = datetime.now().strftime("%H-%M-%S_%d-%m-%Y")
        
        with filename_prefix_lock:
            custom_prefix = custom_filename_prefix
        
        if custom_prefix:
            target_filename = f"{custom_prefix}_labview_video_{timestamp}.mp4"
        else:
            target_filename = f"labview_video_{timestamp}.mp4"
        
        if copy_file_to_pc_transfer(source_path, target_filename):
            # If POST request, return file content
            if request.method == 'POST':
                file_path = os.path.join("pc_transfer", target_filename)
                return send_file(file_path, as_attachment=True, download_name=target_filename)
            else:
                # GET request returns file information
                return jsonify({
                    "status": "success", 
                    "filename": target_filename,
                    "message": "Latest video ready for transfer",
                    "download_url": f"/api/download/{target_filename}"
                })
        else:
            return jsonify({"status": "error", "message": "Failed to copy video"}), 500
            
    except Exception as e:
        logger.error(f"LabVIEW video transfer error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/labview/status')
def labview_status():
    """
    LabVIEW dedicated status interface - returns simple status information
    """
    with temperature_lock:
        temp = current_temperature
    
    with labview_lock:
        duration = labview_recording_duration
    
    with filename_prefix_lock:
        prefix = custom_filename_prefix
    
    return jsonify({
        "camera_ready": camera is not None,
        "recording_active": is_recording,
        "recording_duration": duration,
        "temperature": temp,
        "filename_prefix": prefix,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/labview/simple_record', methods=['GET'])
def labview_simple_record():
    """
    LabVIEW simplified recording interface - uses URL parameters
    """
    global is_recording, recording_thread

    duration = request.args.get('duration', type=int, default=30)
    duration = max(1, duration)
    
    if is_recording:
        return jsonify({"status": "error", "message": "Recording already in progress"}), 400
    
    try:
        # Generate filename with custom prefix
        filename = get_filename(f"labview_simple_{duration}s", "video", "mp4")
        filepath = os.path.join("recordings", filename)
        
        is_recording = True
        recording_thread = threading.Thread(
            target=recording_worker, 
            args=(filepath, duration)
        )
        recording_thread.daemon = True
        recording_thread.start()
        
        return jsonify({
            "status": "success", 
            "message": f"Recording started for {duration} seconds",
            "filename": filename,
            "duration": duration
        })
        
    except Exception as e:
        logger.error(f"LabVIEW simple recording error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# PC Transfer API endpoints
@app.route('/api/transfer/latest_image')
def api_transfer_latest_image():
    """Transfer latest image to PC"""
    try:
        latest_image = get_latest_file("images", ".jpg")
        if not latest_image:
            return jsonify({"status": "error", "message": "No image files found"}), 404
        
        source_path = os.path.join("images", latest_image)
        timestamp = datetime.now().strftime("%H-%M-%S_%d-%m-%Y")
        
        with filename_prefix_lock:
            custom_prefix = custom_filename_prefix
        
        if custom_prefix:
            target_filename = f"{custom_prefix}_image_{timestamp}.jpg"
        else:
            target_filename = f"image_{timestamp}.jpg"
        
        if copy_file_to_pc_transfer(source_path, target_filename):
            return jsonify({
                "status": "success", 
                "filename": target_filename,
                "message": "Latest image transferred successfully"
            })
        else:
            return jsonify({"status": "error", "message": "Failed to copy image"}), 500
            
    except Exception as e:
        logger.error(f"Latest image transfer error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/transfer/latest_video')
def api_transfer_latest_video():
    """Transfer latest video to PC"""
    try:
        latest_video = get_latest_file("recordings", ".mp4")
        if not latest_video:
            return jsonify({"status": "error", "message": "No video files found"}), 404
        
        source_path = os.path.join("recordings", latest_video)
        timestamp = datetime.now().strftime("%H-%M-%S_%d-%m-%Y")
        
        with filename_prefix_lock:
            custom_prefix = custom_filename_prefix
        
        if custom_prefix:
            target_filename = f"{custom_prefix}_video_{timestamp}.mp4"
        else:
            target_filename = f"video_{timestamp}.mp4"
        
        if copy_file_to_pc_transfer(source_path, target_filename):
            return jsonify({
                "status": "success", 
                "filename": target_filename,
                "message": "Latest video transferred successfully"
            })
        else:
            return jsonify({"status": "error", "message": "Failed to copy video"}), 500
            
    except Exception as e:
        logger.error(f"Latest video transfer error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/transfer/all_images')
def api_transfer_all_images():
    """Transfer all images to PC"""
    try:
        image_files = []
        for file in os.listdir("images"):
            if file.endswith(".jpg"):
                source_path = os.path.join("images", file)
                target_filename = f"image_{file}"
                if copy_file_to_pc_transfer(source_path, target_filename):
                    image_files.append(target_filename)
        
        if not image_files:
            return jsonify({"status": "error", "message": "No image files found"}), 404
        
        # Create ZIP archive
        timestamp = datetime.now().strftime("%H-%M-%S_%d-%m-%Y")
        
        with filename_prefix_lock:
            custom_prefix = custom_filename_prefix
        
        if custom_prefix:
            archive_name = f"{custom_prefix}_all_images_{timestamp}.zip"
        else:
            archive_name = f"all_images_{timestamp}.zip"
        
        if create_zip_archive(image_files, archive_name):
            return jsonify({
                "status": "success", 
                "filename": archive_name,
                "message": f"All {len(image_files)} images transferred successfully"
            })
        else:
            return jsonify({"status": "error", "message": "Failed to create archive"}), 500
            
    except Exception as e:
        logger.error(f"All images transfer error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/transfer/all_videos')
def api_transfer_all_videos():
    """Transfer all videos to PC"""
    try:
        video_files = []
        for file in os.listdir("recordings"):
            if file.endswith(".mp4"):
                source_path = os.path.join("recordings", file)
                target_filename = f"video_{file}"
                if copy_file_to_pc_transfer(source_path, target_filename):
                    video_files.append(target_filename)
        
        if not video_files:
            return jsonify({"status": "error", "message": "No video files found"}), 404
        
        # Create ZIP archive
        timestamp = datetime.now().strftime("%H-%M-%S_%d-%m-%Y")
        
        with filename_prefix_lock:
            custom_prefix = custom_filename_prefix
        
        if custom_prefix:
            archive_name = f"{custom_prefix}_all_videos_{timestamp}.zip"
        else:
            archive_name = f"all_videos_{timestamp}.zip"
        
        if create_zip_archive(video_files, archive_name):
            return jsonify({
                "status": "success", 
                "filename": archive_name,
                "message": f"All {len(video_files)} videos transferred successfully"
            })
        else:
            return jsonify({"status": "error", "message": "Failed to create archive"}), 500
            
    except Exception as e:
        logger.error(f"All videos transfer error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/transfer/capture_video')
def api_capture_and_transfer_video():
    """Record video with specified duration and transfer to PC"""
    global is_recording, recording_thread
    
    if not camera:
        return jsonify({"status": "error", "message": "Camera not initialized"}), 500
    
    if is_recording:
        return jsonify({"status": "error", "message": "Recording already in progress"}), 400
    
    try:
        duration = request.args.get('duration', type=int, default=10)
        
        # Generate filename with custom prefix
        filename = get_filename(f"transfer_{duration}s", "video", "mp4")
        filepath = os.path.join("recordings", filename)
        
        pc_filename = get_filename(f"custom_{duration}s", "video", "mp4")
        
        is_recording = True
        recording_thread = threading.Thread(
            target=recording_worker, 
            args=(filepath, duration)
        )
        recording_thread.daemon = True
        recording_thread.start()
        
        # Wait for recording to complete
        recording_thread.join()
        
        # Copy to PC transfer directory
        if copy_file_to_pc_transfer(filepath, pc_filename):
            return jsonify({
                "status": "success", 
                "filename": pc_filename,
                "message": f"Custom {duration}s video recorded and transferred successfully"
            })
        else:
            return jsonify({"status": "error", "message": "Failed to transfer video"}), 500
            
    except Exception as e:
        logger.error(f"Custom video capture/transfer error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/download/<filename>')
def api_download_file(filename):
    """Download file API"""
    try:
        file_path = os.path.join("pc_transfer", filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"status": "error", "message": "File not found"}), 404
    except Exception as e:
        logger.error(f"File download error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def main():
    """Main function"""
    logger.info("Starting Raspberry Pi Comprehensive Monitoring Service...")
    
    # Initialize temperature sensor
    device_file = init_temperature_sensor()
    
    # Start temperature monitoring thread
    if device_file:
        temp_thread = threading.Thread(target=temperature_monitor, args=(device_file,))
        temp_thread.daemon = True
        temp_thread.start()
        logger.info("Temperature monitoring thread started")
    else:
        logger.warning("Unable to start temperature monitoring")
    
    # Initialize camera
    camera_ready = init_camera()
    
    # Start camera capture thread
    if camera_ready:
        capture_thread = threading.Thread(target=camera_capture_loop)
        capture_thread.daemon = True
        capture_thread.start()
        logger.info("Camera capture thread started")
    else:
        logger.warning("Unable to start camera capture")
    
    # Start Flask application
    try:
        logger.info("Starting Flask server (0.0.0.0:5000)...")
        logger.info("New features:")
        logger.info("  - Custom filename prefixes")
        logger.info("  - New timestamp format: HH-MM-SS_DD-MM-YYYY")
        logger.info("LabVIEW integration endpoints available:")
        logger.info("  GET  /labview/control - Get status and parameters")
        logger.info("  POST /labview/control - Execute control commands")
        logger.info("  POST /labview/record_with_duration - Record with specified duration")
        logger.info("  GET  /labview/transfer_latest_video - Transfer latest video")
        logger.info("  GET  /labview/status - Get system status")
        logger.info("  GET  /labview/simple_record?duration=30 - Simplified recording interface")
        
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
    except Exception as e:
        logger.error(f"Server startup error: {e}")
    finally:
        # Cleanup resources
        if camera:
            camera.stop()
        logger.info("Program exited")

if __name__ == '__main__':
    main()