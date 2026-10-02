import asyncio
import fractions
import json
import os
import ssl
import sys
import time
from aiohttp import web
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
import av
from Xlib import X, display
from Xlib.ext import xtest

ROOT = os.path.dirname(__file__)

pcs = set()

# Initialize Xlib for mouse input control
try:
    x_display = display.Display()
    x_screen = x_display.screen()
    x_root = x_screen.root
    SCREEN_WIDTH = x_screen.width_in_pixels
    SCREEN_HEIGHT = x_screen.height_in_pixels
    print(f"Xlib display connected: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
except Exception as e:
    x_display = None
    SCREEN_WIDTH = 1366
    SCREEN_HEIGHT = 768
    print(f"Warning: Xlib initialization failed: {e}")

class DesktopStreamTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, display=":0.0"):
        super().__init__()
        self.display = display
        self.container = av.open(
            display,
            format="x11grab",
            options={
                "framerate": "30",
                "video_size": f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}",
                "draw_mouse": "1"
            }
        )
        self.stream = self.container.streams.video[0]
        self._start_time = None
        self._frame_count = 0
        self.demuxer = self.container.demux(self.stream)

    async def recv(self):
        loop = asyncio.get_event_loop()
        def get_next_frame():
            for packet in self.demuxer:
                for frame in packet.decode():
                    return frame
            return None

        frame = await loop.run_in_executor(None, get_next_frame)

        if self._start_time is None:
            self._start_time = time.time()

        pts = int((time.time() - self._start_time) * 90000)
        frame.pts = pts
        frame.time_base = fractions.Fraction(1, 90000)
        self._frame_count += 1

        return frame

async def index(request):
    try:
        with open(os.path.join(ROOT, "static", "index.html"), "r") as f:
            content = f.read()
        return web.Response(content_type="text/html", text=content)
    except Exception as e:
        return web.Response(status=500, text=str(e))

async def mouse_input(request):
    if not x_display:
        return web.json_response({"status": "error", "message": "X display unavailable"}, status=500)
    try:
        data = await request.json()
        action = data.get("action")

        if action == "move":
            # Normalized coordinates (0.0 to 1.0)
            norm_x = max(0.0, min(1.0, float(data.get("x", 0))))
            norm_y = max(0.0, min(1.0, float(data.get("y", 0))))
            target_x = int(norm_x * SCREEN_WIDTH)
            target_y = int(norm_y * SCREEN_HEIGHT)
            x_root.warp_pointer(target_x, target_y)
            x_display.sync()

        elif action == "click":
            button = int(data.get("button", 1)) # 1: left, 3: right
            xtest.fake_input(x_display, X.ButtonPress, button)
            x_display.sync()
            xtest.fake_input(x_display, X.ButtonRelease, button)
            x_display.sync()

        elif action == "down":
            button = int(data.get("button", 1))
            xtest.fake_input(x_display, X.ButtonPress, button)
            x_display.sync()

        elif action == "up":
            button = int(data.get("button", 1))
            xtest.fake_input(x_display, X.ButtonRelease, button)
            x_display.sync()

        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400)

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    config = RTCConfiguration(iceServers=[
        RTCIceServer(urls=["stun:stun.l.google.com:19302"])
    ])
    pc = RTCPeerConnection(configuration=config)
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        if pc.connectionState in ("failed", "closed"):
            await pc.close()
            pcs.discard(pc)

    try:
        track = DesktopStreamTrack(display=":0.0")
        pc.addTrack(track)
    except Exception as e:
        sys.stderr.write(f"Error adding track: {e}\n")

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    for _ in range(10):
        if pc.iceGatheringState == "complete":
            break
        await asyncio.sleep(0.1)

    return web.Response(
        content_type="application/json",
        text=json.dumps({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}),
    )

async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

def create_app():
    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_post("/offer", offer)
    app.router.add_post("/input/mouse", mouse_input)
    app.router.add_static("/static/", path=os.path.join(ROOT, "static"), name="static")
    return app

if __name__ == "__main__":
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(
        os.path.join(ROOT, "cert.pem"),
        os.path.join(ROOT, "key.pem")
    )
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8443, ssl_context=ssl_context)
