import os
import io
import pyaudio
import wave
from dotenv import load_dotenv
from google.cloud import speech

# .env dosyasındaki değişkenleri yükleyin
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Ses kaydı ayarları
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Google Cloud Speech-to-Text için önerilen sample rate


def record_and_convert():
    """Mikrofondan ses kaydı yapar ve Google Cloud STT ile metne dönüştürür."""
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("Lütfen konuşun...")
    frames = []

    try:
        # 5 saniye ses kaydı yapın (daha uzun veya kısa yapabilirsiniz)
        for i in range(0, int(RATE / CHUNK * 5)):
            data = stream.read(CHUNK)
            frames.append(data)
    except KeyboardInterrupt:
        print("Kayıt durduruldu.")

    print("Kayıt tamamlandı.")

    # Kaydı durdur ve ses akışını kapat
    stream.stop_stream()
    stream.close()
    p.terminate()

    # Ses verisini bir ByteIO nesnesine yaz
    audio_data = b''.join(frames)
    audio_stream = io.BytesIO(audio_data)

    # Google Cloud STT istemcisini oluştur
    client = speech.SpeechClient()

    # Ses dosyasını API'ye gönder
    audio = speech.RecognitionAudio(content=audio_data)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="tr-TR",
    )

    print("Ses metne dönüştürülüyor...")
    try:
        response = client.recognize(config=config, audio=audio)
        for result in response.results:
            text = result.alternatives[0].transcript
            print("Dönüştürülen metin: " + text)
            return text
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return None


if __name__ == "__main__":
    user_text = record_and_convert()
    if user_text:
        print(f"Başarılı bir şekilde metne dönüştürüldü: '{user_text}'")