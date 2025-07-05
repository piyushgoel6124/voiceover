from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from gtts import gTTS
import pysrt, ffmpeg, uuid, os

app = FastAPI()
OUT_DIR = "/tmp"

class NarrationRequest(BaseModel):
    text: str

def generate_subtitles(text, voice_path, srt_path):
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    subs = pysrt.SubRipFile()
    t = 0.0
    for i, sent in enumerate(sentences, start=1):
        duration = max(len(sent.split()) / 2.0, 2)
        sub = pysrt.SubRipItem(index=i,
                               start=pysrt.SubRipTime(seconds=t),
                               end=pysrt.SubRipTime(seconds=t+duration),
                               text=sent)
        subs.append(sub)
        t += duration
    subs.save(srt_path, encoding='utf-8')

@app.post("/narrate")
async def narrate(req: NarrationRequest):
    uid = uuid.uuid4().hex
    txt = req.text
    voice_path = os.path.join(OUT_DIR, f"{uid}_voice.mp3")
    srt_path = os.path.join(OUT_DIR, f"{uid}.srt")
    out_mp4 = os.path.join(OUT_DIR, f"{uid}_overlay.mp4")

    # Generate TTS
    gTTS(txt).save(voice_path)

    # Generate .srt
    generate_subtitles(txt, voice_path, srt_path)

    # Create subtitle overlay video
    (
        ffmpeg
        .input('color=black@0.0:s=720x1280:d=0.1', f='lavfi')
        .output(out_mp4,
                i=voice_path,
                vf=f"subtitles='{srt_path}':force_style='Fontsize=48,PrimaryColour=&HFFFFFF&'",
                acodec='aac',
                vcodec='libx264',
                pix_fmt='yuva420p',
                shortest=None,
                **{'y': None})
        .run(overwrite_output=True)
    )

    return {"overlay_url": f"/tmp/{os.path.basename(out_mp4)}"}
