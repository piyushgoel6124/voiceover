from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from gtts import gTTS
import ffmpeg
import uuid
import os

app = FastAPI()

@app.post("/generate_voice/")
async def generate_voice(req: Request):
    data = await req.json()
    text = data.get("text", "").strip()

    if not text:
        return {"error": "Missing text"}

    uid = str(uuid.uuid4())
    voice_mp3 = f"temp_{uid}.mp3"
    voice_wav = f"temp_{uid}.wav"

    try:
        # Generate MP3 using gTTS
        tts = gTTS(text=text, lang="en")
        tts.save(voice_mp3)

        # Convert MP3 to WAV using ffmpeg-python
        ffmpeg.input(voice_mp3).output(voice_wav).run(overwrite_output=True)

        # Serve the WAV file
        return FileResponse(path=voice_wav, media_type="audio/wav", filename="voice.wav")

    except Exception as e:
        return {"error": str(e)}

    finally:
        # Clean up files after response (best effort)
        def safe_unlink(path):
            try:
                os.remove(path)
            except:
                pass

        safe_unlink(voice_mp3)
        # Comment the below line if you want to let client download it first
        # safe_unlink(voice_wav)
