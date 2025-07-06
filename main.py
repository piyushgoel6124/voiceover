from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from gtts import gTTS
import uuid
import os
import threading
import time

app = FastAPI()

def remove_file_later(path, delay=10):
    def delayed_delete():
        time.sleep(delay)
        try:
            os.remove(path)
            print(f"🧹 Deleted: {path}")
        except Exception as e:
            print(f"⚠️ Failed to delete {path}: {e}")
    threading.Thread(target=delayed_delete).start()

@app.get("/")
async def root():
    return JSONResponse(content={"status": "ok", "message": "Voiceover API is live 🎙️"})

@app.post("/generate")
async def generate_audio(request: Request):
    try:
        data = await request.json()
        text = data.get("text")
        if not text:
            return JSONResponse(status_code=400, content={"error": "No text provided"})

        filename = f"{uuid.uuid4()}.mp3"
        tts = gTTS(text)
        tts.save(filename)

        remove_file_later(filename, delay=10)

        return FileResponse(
            path=filename,
            filename="voiceover.mp3",
            media_type="audio/mpeg"
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
