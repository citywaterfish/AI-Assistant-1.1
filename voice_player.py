import os
import io
import random
import threading
import asyncio
import edge_tts
import sounddevice as sd
import soundfile as sf
from PIL import Image, ImageTk
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import re
import html

# ---------------- TEXT NORMALIZATION ---------------- #

def normalize_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return html.escape(text)  # SSML güvenliği

# ---------------- SSML BUILDER ---------------- #

def build_ssml(text: str, voice: str) -> str:
    return (
        f'<speak version="1.0" xml:lang="en-US">'
        f'<voice name="{voice}">'
        f'{text}'
        f'</voice>'
        f'</speak>'
    )

# ---------------- UI CLASS ---------------- #

class VoiceImagePlayer:
    def __init__(self, face_path, size=(760, 760)):
        self.root = tk.Tk()
        self.root.title("AI - EPISODE 2")
        self.root.resizable(False, False)
        self.root.geometry("760x900")

        self.fixed_size = size
        self.face_original = Image.open(face_path).resize(self.fixed_size, Image.LANCZOS)

        self.face_label = tk.Label(self.root, bg="#001f4d", borderwidth=0)
        self.face_label.place(relx=0.5, rely=0.4, anchor="center")

        self.scale = 1.0
        self.playing = False

        self.text_box = ScrolledText(
            self.root,
            fg="#00ffff",
            bg="#001f4d",
            insertbackground="#00ffff",
            height=12,
            borderwidth=0,
            wrap="word",
            font=("Consolas", 10),
            padx=10,
            pady=10
        )
        self.text_box.place(relx=0.5, rely=0.85, anchor="center")
        self.text_box.configure(state="disabled")

        self.animate()
        self.root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))

    # 🔥 BU METOT EKSİKTİ – ŞİMDİ VAR
    def write_log(self, text: str):
        self.text_box.configure(state="normal")
        self.text_box.insert(tk.END, text + "\n")
        self.text_box.see(tk.END)
        self.text_box.configure(state="disabled")

    def start_animation(self):
        self.playing = True

    def stop_animation(self):
        self.playing = False

    def animate(self):
        if self.playing:
            self.scale += random.uniform(-0.01, 0.015)
            self.scale = min(max(self.scale, 1.02), 1.08)
        else:
            self.scale += (1.0 - self.scale) * 0.1

        w, h = self.fixed_size
        resized = self.face_original.resize(
            (int(w * self.scale), int(h * self.scale)),
            Image.LANCZOS
        )

        img = ImageTk.PhotoImage(resized)
        self.face_label.configure(image=img)
        self.face_label.image = img

        self.root.after(50, self.animate)

# ---------------- VOICE ENGINE ---------------- #

VOICE = "en-GB-RyanNeural"
  # Erkek, stabil

def edge_speak(text: str, img_player: VoiceImagePlayer, voice: str = VOICE):
    if not text.strip():
        return

    clean_text = text.strip()

    def _thread():
        async def _run():
            audio_buffer = bytearray()
            first_audio = False

            try:
                communicate = edge_tts.Communicate(
                    clean_text,
                    voice
                )

                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_buffer.extend(chunk["data"])
                        if not first_audio:
                            first_audio = True
                            img_player.start_animation()

            except Exception as e:
                print("TTS ERROR:", e)
                img_player.stop_animation()
                return

            if not audio_buffer:
                img_player.stop_animation()
                return

            data, samplerate = sf.read(io.BytesIO(audio_buffer), dtype="float32")
            sd.play(data, samplerate)
            sd.wait()
            img_player.stop_animation()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run())
        loop.close()

    threading.Thread(target=_thread, daemon=True).start()
