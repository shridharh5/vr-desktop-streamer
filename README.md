# VR Box & 2D Remote Desktop Streamer

A low-latency, hardware-accelerated remote desktop streamer tailored for mobile browsers and VR Boxes (Google Cardboard / VR Box headsets).

## Features

- **Direct WebRTC Video Stream:** Low-latency 60 FPS desktop streaming with accurate 90kHz RTP Presentation Timestamp (PTS) pacing.
- **Side-by-Side (SBS) VR Split Screen:** Pure dual-viewport layout for VR Box headsets with comfortable lens margins.
- **Instant 2D / VR Mode Switching:** On-screen toggle button or quick double-tap anywhere on screen to flip between fullscreen 2D and VR split screen.
- **Battery & Thermals Optimized:** Renders directly using HTML5 `<video>` elements, routing the stream directly into the phone's dedicated hardware video decoder ASIC (`MediaCodec`) without WebGL/CPU overhead.
- **Fullscreen & Orientation Lock:** One-tap fullscreen mode with automatic landscape locking.

## Project Structure

```
├── generate_certs.py     # Generates self-signed SSL certificate for local HTTPS/WebRTC
├── server.py             # Asynchronous WebRTC streaming and signaling server
├── static/
│   ├── index.html        # Responsive 2D / VR SBS client UI
│   └── js/
│       └── three.min.js  # Three.js library
├── requirements.txt      # Python dependencies
└── vr-webstreamer.service# Systemd user service unit template
```

## Getting Started

### 1. Requirements

- Python 3.10+
- Linux session (Ubuntu Xorg recommended for direct `:0.0` frame grabbing)

### 2. Setup Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Generate Local SSL Certificate

WebRTC and Fullscreen APIs require HTTPS:

```bash
python generate_certs.py
```

### 4. Run the Streamer

```bash
python server.py
```

Open `https://<YOUR-PC-IP>:8443` on your Android or mobile browser (accept the self-signed certificate), and tap **Connect & Start Stream**.

## License

MIT
