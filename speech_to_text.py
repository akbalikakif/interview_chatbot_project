import os
import io
import pyaudio
import wave
import time
from datetime import datetime
from dotenv import load_dotenv
from google.cloud import speech
import numpy as np

# .env dosyasındaki değişkenleri yükle
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Ses kaydı ayarları
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Google Cloud Speech-to-Text için önerilen sample rate

# Sessizlik algılama parametreleri
SILENCE_THRESHOLD = 500  # Sessizlik eşiği (amplitude değeri)
SILENCE_DURATION = 5  # Sessizlik süresi (saniye)
MIN_RECORDING_DURATION = 2  # Minimum kayıt süresi (saniye)

# Data klasörünü oluştur
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def calculate_rms(audio_data):
    """Ses verisinin RMS (Root Mean Square) değerini hesaplar - ses seviyesini ölçmek için"""
    audio_array = np.frombuffer(audio_data, dtype=np.int16)
    rms = np.sqrt(np.mean(audio_array ** 2))
    return rms

def is_silent(audio_data, threshold=SILENCE_THRESHOLD):
    """Ses verisinin sessiz olup olmadığını kontrol eder"""
    rms = calculate_rms(audio_data)
    return rms < threshold

def save_audio_file(frames, filename):
    """Ses kaydını WAV dosyası olarak kaydeder"""
    filepath = os.path.join(DATA_DIR, filename)

    with wave.open(filepath, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    print(f"Ses kaydı kaydedildi: {filepath}")
    return filepath

def record_and_convert(question_number=None):
    """
    Mikrofondan ses kaydı yapar, sessizlik algıladığında durdurur,
    hem dosyaya kaydeder hem de Google Cloud STT ile metne dönüştürür.
    
    Args:
        question_number: Soru numarası (1, 2, 3, ...). Belirtilirse data/soru-{n}.wav olarak kaydedilir.
    """
    p = pyaudio.PyAudio()

    # Mikrofon akışını başlat
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    print("\n Konuşmaya başlayın...")
    print("Sessizlik algılandığında kayıt otomatik durur.\n")

    frames = []
    silent_chunks = 0
    max_silent_chunks = int(SILENCE_DURATION * RATE / CHUNK)
    recording_started = False
    start_time = time.time()

    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
            current_duration = time.time() - start_time

            # Sessizlik kontrolü
            if is_silent(data):
                silent_chunks += 1

                # Minimum süre geçtiyse ve yeterli sessizlik varsa dur
                if current_duration >= MIN_RECORDING_DURATION and silent_chunks >= max_silent_chunks:
                    print(f"\n Sessizlik algılandı. Kayıt tamamlandı. ({current_duration:.1f} saniye)")
                    break
            else:
                # Ses tespit edildi
                if not recording_started:
                    recording_started = True
                    print("Kayıt başladı...")

                silent_chunks = 0  # Sessizlik sayacını sıfırla

            # Maksimum kayıt süresini aşma (güvenlik için 2 dakika)
            if current_duration > 120:
                print("\n Maksimum kayıt süresine ulaşıldı.")
                break

    except KeyboardInterrupt:
        print("\n Kayıt kullanıcı tarafından durduruldu.")

    finally:
        # Akışı kapat
        stream.stop_stream()
        stream.close()
        p.terminate()

    # Eğer çok kısa kayıt varsa uyar
    if len(frames) < int(MIN_RECORDING_DURATION * RATE / CHUNK):
        print("Çok kısa bir kayıt yapıldı. Lütfen tekrar deneyin.")
        return None

    # Ses dosyasını data/ klasörüne kaydet
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if question_number is not None:
        # Soru numarasına göre kaydet (soru-1.wav, soru-2.wav, ...)
        audio_filepath = os.path.join(DATA_DIR, f"soru-{question_number}.wav")
    else:
        # Geçici dosya olarak kaydet
        audio_filepath = os.path.join(DATA_DIR, f"temp_recording_{timestamp}.wav")

    # Ses dosyasını kaydet
    with wave.open(audio_filepath, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    
    print(f"Ses kaydedildi: {audio_filepath}")

    # Ses verisini byte array'e dönüştür
    audio_data = b''.join(frames)

    # Google Cloud STT istemcisini oluştur
    print("\nSes metne dönüştürülüyor...")
    client = speech.SpeechClient()

    # Ses dosyasını API'ye gönder
    audio = speech.RecognitionAudio(content=audio_data)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="tr-TR",
        enable_automatic_punctuation=True,  # Otomatik noktalama
        model="default",  # Daha iyi sonuçlar için
    )

    try:
        response = client.recognize(config=config, audio=audio)

        if not response.results:
            print(" Ses algılandı ancak metin dönüştürülemedi. Lütfen daha net konuşun.")
            return None

        # En yüksek güvenilirlik skoruna sahip transkripsiyonu al
        transcript = response.results[0].alternatives[0].transcript
        confidence = response.results[0].alternatives[0].confidence

        print(f"\n Dönüştürülen metin: '{transcript}'")
        print(f"Güvenilirlik skoru: {confidence:.2%}\n")

        return {
            'transcript': transcript,
            'confidence': confidence,
            'audio_file': audio_filepath,  # Dosya yolu döndürülür
            'timestamp': timestamp
        }

    except Exception as e:
        print(f" Hata oluştu: {e}")
        return None

