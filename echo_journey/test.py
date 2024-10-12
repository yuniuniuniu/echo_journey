import sys
sys.path.append("/root/echo_journey")
from echo_journey.audio.text_to_speech.kanyun_tts import KanyunTTS



import asyncio

print(asyncio.run(KanyunTTS().generate_audio("你好")))