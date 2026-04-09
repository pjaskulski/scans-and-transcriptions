import os
import wave

from pydub import AudioSegment

from app.paths import mp3_for_image, wav_for_image
from services.cache_service import load_cache
from services.gemini_service import synthesize_speech


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def convert_wav_to_mp3(input_file, output_file):
    audio = AudioSegment.from_raw(
        input_file,
        sample_width=2,
        frame_rate=24000,
        channels=1,
    )
    audio.export(output_file, format="mp3", bitrate="128k")


def audio_needs_generation(image_path: str, json_path: str | None, checksum: str) -> bool:
    mp3_path = str(mp3_for_image(image_path))
    if not os.path.exists(mp3_path) or not json_path or not os.path.exists(json_path):
        return True

    cache_data = load_cache(json_path)
    return cache_data.get("tts_checksum") != checksum


def generate_mp3_from_text(
    api_key: str,
    text: str,
    image_path: str,
    voice_name: str = "Enceladus",
    model_name: str = "gemini-2.5-flash-preview-tts",
):
    wav_path = str(wav_for_image(image_path))
    mp3_path = str(mp3_for_image(image_path))

    model, response = synthesize_speech(api_key, text, voice_name=voice_name, model_name=model_name)
    data = response.candidates[0].content.parts[0].inline_data.data

    wave_file(wav_path, data)
    convert_wav_to_mp3(wav_path, mp3_path)
    os.remove(wav_path)

    return model, response, mp3_path
