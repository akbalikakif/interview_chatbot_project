

import os
import io
import wave
import pyaudio
from dotenv import load_dotenv
from google.cloud import texttospeech

# .env dosyasındaki değişkenleri yükleyin
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


def text_to_speech_playback(text):
    """
    Verilen metni Google Cloud TTS API'si ile sese dönüştürür ve oynatır.

    Args:
        text (str): Sese dönüştürülecek metin.
    """
    try:
        # Google Cloud TTS istemcisini oluştur
        client = texttospeech.TextToSpeechClient()

        # Metin girdisini tanımla
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Sesin özelliklerini (dil, cinsiyet vb.) ayarla
        voice = texttospeech.VoiceSelectionParams(
            language_code="tr-TR",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL  # Veya FEMALE/MALE
        )

        # Ses çıkışı formatını tanımla
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )

        # API isteğini gönder
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        # Gelen ses verisini bir WAVE dosyası olarak kaydet
        with open("output.wav", "wb") as out:
            out.write(response.audio_content)

        # Sesi oynatmak için PyAudio'yu kullan
        print("Yanıt oynatılıyor...")
        p = pyaudio.PyAudio()

        with wave.open('output.wav', 'rb') as wf:
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)

            data = wf.readframes(1024)
            while data:
                stream.write(data)
                data = wf.readframes(1024)

        stream.stop_stream()
        stream.close()
        p.terminate()

    except Exception as e:
        print(f"TTS API hatası: {e}")


if __name__ == "__main__":
    test_text = "Merhaba, bir bilgisayar mühendisliği mülakatına hoş geldiniz. Hazır olduğunuzda konuşabilirsiniz."
    text_to_speech_playback(test_text)