from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import FileResponse
from gtts import gTTS
import ffmpeg, pysrt, uuid, os, random

app = FastAPI()
OUT_DIR = "/tmp"
SS_DIR = "./ss"  # Place your Subway Surfer videos here

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
    return t  # total duration of script

@app.post("/narrate")
async def narrate(req: NarrationRequest):
    uid = uuid.uuid4().hex
    text = req.text

    voice_path = os.path.join(OUT_DIR, f"{uid}_voice.mp3")
    srt_path = os.path.join(OUT_DIR, f"{uid}.srt")
    overlay_path = os.path.join(OUT_DIR, f"{uid}_overlay.mp4")
    final_path = os.path.join(OUT_DIR, f"{uid}_final.mp4")

    # Generate voice
    gTTS(text).save(voice_path)

    # Generate subtitles
    duration = generate_subtitles(text, srt_path)

    # Create transparent overlay with voice and subs
    (
        ffmpeg
        .input('color=black@0.0:s=720x1280:d={}'.format(duration), f='lavfi')
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

    # Choose random Subway Surfer clip
    subway_clip = random.choice([os.path.join(SS_DIR, f) for f in os.listdir(SS_DIR) if f.endswith(".mp4")])

    # Trim background to match audio duration
    trimmed_ss = os.path.join(OUT_DIR, f"{uid}_bg_trimmed.mp4")
    (
        ffmpeg
        .input(subway_clip)
        .output(trimmed_ss, t=duration, y=None)
        .run()
    )

    # Overlay the voice+subtitles over Subway Surfer
    (
        ffmpeg
        .input(trimmed_ss)
        .input(overlay_path)
        .filter_complex("[0:v][1:v] overlay=0:0")
        .output(final_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None, y=None)
        .run()
    )

    return {"final_video_url": f"/output/{os.path.basename(final_path)}"}

@app.get("/output/{filename}")
def serve_output_file(filename: str):
    path = os.path.join(OUT_DIR, filename)
    return FileResponse(path, media_type="video/mp4")
