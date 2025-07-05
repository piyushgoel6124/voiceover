from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import FileResponse
from gtts import gTTS
import ffmpeg, pysrt, uuid, os, random, requests

app = FastAPI()
OUT_DIR = "/tmp"

DROPBOX_CLIPS = [
    "https://www.dropbox.com/scl/fi/xm6jnoddq3cz3ms9tr19i/1.mp4?raw=1",
    "https://www.dropbox.com/scl/fi/touw1m2pi1knk7xhbvcip/2.mp4?raw=1",
    "https://www.dropbox.com/scl/fi/3ae6zxy49xhrf78qzarqi/3.mp4?raw=1",
    "https://www.dropbox.com/scl/fi/yisak216d9smf29x3hukg/4.mp4?raw=1",
    "https://www.dropbox.com/scl/fi/1d3i3qgv17u8swj2kqh5c/5.mp4?raw=1",
    "https://www.dropbox.com/scl/fi/q0iqv2eaogwxea6djl7iv/6.mp4?raw=1",
    "https://www.dropbox.com/scl/fi/61hxbubhmoktjoeb0ewjm/7.mp4?raw=1",
    "https://www.dropbox.com/scl/fi/d0oj89f6y3vpzxyf8126p/8.mp4?raw=1",
    "https://www.dropbox.com/scl/fi/7abb22yzw74ikbpug7wqf/9.mp4?raw=1",
    "https://www.dropbox.com/scl/fi/ztje3cq6neq2x2fa4wamg/10.mp4?raw=1"
]

class NarrationRequest(BaseModel):
    text: str

def generate_subtitles(text, srt_path):
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    subs = pysrt.SubRipFile()
    t = 0.0
    for i, sent in enumerate(sentences, start=1):
        duration = max(len(sent.split()) / 2.0, 2)
        sub = pysrt.SubRipItem(index=i,
                               start=pysrt.SubRipTime(seconds=t),
                               end=pysrt.SubRipTime(seconds=t + duration),
                               text=sent)
        subs.append(sub)
        t += duration
    subs.save(srt_path, encoding='utf-8')
    return t

def download_video(url, dest_path):
    r = requests.get(url, stream=True)
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

@app.post("/narrate")
async def narrate(req: NarrationRequest):
    uid = uuid.uuid4().hex
    text = req.text

    voice_path = os.path.join(OUT_DIR, f"{uid}_voice.mp3")
    srt_path = os.path.join(OUT_DIR, f"{uid}.srt")
    overlay_path = os.path.join(OUT_DIR, f"{uid}_overlay.mp4")
    bg_path = os.path.join(OUT_DIR, f"{uid}_bg.mp4")
    trimmed_bg = os.path.join(OUT_DIR, f"{uid}_bg_trimmed.mp4")
    final_output = os.path.join(OUT_DIR, f"{uid}_final.mp4")

    # 1. Generate voice
    gTTS(text).save(voice_path)

    # 2. Generate subs
    duration = generate_subtitles(text, srt_path)

    # 3. Create transparent voice+subtitles overlay
    (
        ffmpeg
        .input(f"color=black@0.0:s=720x1280:d={duration}", f='lavfi')
        .output(overlay_path,
                i=voice_path,
                vf=f"subtitles='{srt_path}':force_style='Fontsize=48,PrimaryColour=&HFFFFFF&'",
                acodec='aac',
                vcodec='libx264',
                pix_fmt='yuva420p',
                shortest=None,
                y=None)
        .run()
    )

    # 4. Pick + download random Subway Surfer clip
    dropbox_url = random.choice(DROPBOX_CLIPS)
    download_video(dropbox_url, bg_path)

    # 5. Trim background to voice length
    (
        ffmpeg
        .input(bg_path)
        .output(trimmed_bg, t=duration, y=None)
        .run()
    )

    # 6. Overlay subtitles+voice on Subway Surfer
    (
        ffmpeg
        .input(trimmed_bg)
        .input(overlay_path)
        .filter_complex("[0:v][1:v] overlay=0:0")
        .output(final_output, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None, y=None)
        .run()
    )

    return {"video_url": f"/output/{os.path.basename(final_output)}"}

@app.get("/output/{filename}")
def serve_output_file(filename: str):
    file_path = os.path.join(OUT_DIR, filename)
    return FileResponse(file_path, media_type="video/mp4")
