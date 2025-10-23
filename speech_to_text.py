"""
speech_to_text.py
Google Cloud Speech-to-Text API kullanarak ses kaydını metne dönüştürür.

Özellikler:
- Çok dilli algılama (Türkçe + İngilizce)
- Otomatik sessizlik algılama
- Gelişmiş model (latest_long) kullanımı
- Teknik terimlerin doğru algılanması
"""

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
SILENCE_DURATION = int(3 * RATE / CHUNK)  # 3 saniye sessizlik (chunk sayısı)
MIN_RECORDING_DURATION = 2  # Minimum kayıt süresi (saniye)
INITIAL_GRACE_PERIOD = int(3 * RATE / CHUNK)  # Başlangıçta 3 saniye bekleme (konuşmaya hazırlanma)

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
    Mikrofondan ses kaydı yapar ve Google Cloud STT Streaming API ile
    gerçek zamanlı olarak metne dönüştürür.
    
    Args:
        question_number: Soru numarası (1, 2, 3, ...). Belirtilirse data/soru-{n}.wav olarak kaydedilir.
    
    Returns:
        Dict: {
            'transcript': str,
            'confidence': float,
            'detected_language': str,
            'audio_file': str,
            'timestamp': str
        }
    """
    print("\n🎤 Konuşmaya başlayın... (Sessizlik algılandığında kayıt otomatik durur)")
    
    # Google Cloud STT streaming client
    client = speech.SpeechClient()
    
    config = speech.StreamingRecognitionConfig(
        config=speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=RATE,
            language_code="tr-TR",
            alternative_language_codes=["en-US"],
            enable_automatic_punctuation=True,
            model="latest_long",
            use_enhanced=True,
        ),
        interim_results=True,  # Ara sonuçları göster (gerçek zamanlı)
    )
    
    # Paylaşılan değişkenler
    frames_for_file = []
    audio_filepath = None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Ses akışı için generator
    def audio_generator():
        """Mikrofon akışından ses verisi üretir ve API'ye gönderir"""
        nonlocal frames_for_file, audio_filepath
        
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        silent_chunks = 0
        recording_started = False
        grace_period_chunks = 0  # Başlangıç toleransı için sayaç
        
        try:
            while True:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames_for_file.append(data)
                grace_period_chunks += 1
                
                # Ses seviyesini kontrol et
                audio_data = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio_data).mean()
                
                # Başlangıç tolerans süresi (ilk 3 saniye)
                if grace_period_chunks <= INITIAL_GRACE_PERIOD:
                    # İlk 3 saniyede ses algılanırsa kayda başla
                    if volume > SILENCE_THRESHOLD and not recording_started:
                        recording_started = True
                        print("🔴 Kayıt başladı...", flush=True)
                    # İlk 3 saniyede sessizlik sayılmaz
                    continue
                
                # Normal kayıt modu (3 saniye sonra)
                if volume > SILENCE_THRESHOLD:
                    silent_chunks = 0
                    if not recording_started:
                        recording_started = True
                        print("🔴 Kayıt başladı...", flush=True)
                else:
                    if recording_started:
                        silent_chunks += 1
                
                # Sessizlik süresi aşıldıysa dur (3 saniye sessizlik)
                if recording_started and silent_chunks > SILENCE_DURATION:
                    print("✅ Kayıt tamamlandı. ({:.1f} saniye)".format(len(frames_for_file) * CHUNK / RATE), flush=True)
                    break
                
                # Maksimum süre kontrolü
                if len(frames_for_file) > (RATE / CHUNK * 60):
                    print("⏱️ Maksimum süre aşıldı.")
                    break
                
                # API'ye gerçek zamanlı gönder
                yield speech.StreamingRecognizeRequest(audio_content=data)
        
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # Ses dosyasını kaydet
            if question_number is not None:
                audio_filepath = os.path.join(DATA_DIR, f"soru-{question_number}.wav")
            else:
                audio_filepath = os.path.join(DATA_DIR, f"temp_recording_{timestamp}.wav")
            
            p_temp = pyaudio.PyAudio()
            with wave.open(audio_filepath, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(p_temp.get_sample_size(pyaudio.paInt16))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames_for_file))
            p_temp.terminate()
            
            print(f"💾 Ses kaydedildi: {audio_filepath}")
    
    # Streaming recognition başlat
    print("🔄 Gerçek zamanlı transkripsiyon aktif...")
    
    try:
        requests = audio_generator()
        responses = client.streaming_recognize(config, requests)
        
        # Sonuçları topla
        transcript = ""
        confidence = 0.0
        detected_language = "tr-TR"
        
        for response in responses:
            if not response.results:
                continue
            
            result = response.results[0]
            
            # Final sonucu al
            if result.is_final:
                transcript = result.alternatives[0].transcript
                confidence = result.alternatives[0].confidence
                
                # Dil tespiti
                if hasattr(result, 'language_code'):
                    detected_language = result.language_code
                
                print(f"📝 {transcript}", flush=True)
            else:
                # Ara sonuçları göster (opsiyonel)
                interim_transcript = result.alternatives[0].transcript
                print(f"⏳ {interim_transcript}", end='\r', flush=True)
        
        if not transcript:
            print("\n⚠️ Ses algılandı ancak metin dönüştürülemedi. Lütfen daha net konuşun.")
            return None
        
        language_name = "Türkçe" if detected_language.startswith("tr") else "İngilizce"
        
        print(f"\n✅ Transkripsiyon tamamlandı!")
        print(f"   Metin: '{transcript}'")
        print(f"   Dil: {language_name} ({detected_language})")
        print(f"   Güvenilirlik: {confidence:.2%}\n")
        
        return {
            'transcript': transcript,
            'confidence': confidence,
            'detected_language': detected_language,
            'audio_file': audio_filepath,
            'timestamp': timestamp
        }
    
    except Exception as e:
        print(f"\n❌ Hata oluştu: {e}")
        return None

