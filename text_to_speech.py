

import os
import io
import wave
import pyaudio
from dotenv import load_dotenv
from google.cloud import texttospeech

# .env dosyasındaki değişkenleri yükleyin
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


def text_to_speech_playback(text, question_number=None, save_to_data=False):
    """
    Verilen metni Google Cloud TTS API'si ile sese dönüştürür ve oynatır.

    Args:
        text (str): Sese dönüştürülecek metin.
        question_number (int): Soru numarası (1, 2, 3, ...). Belirtilirse data/soru-sesi-{n}.wav olarak kaydedilir.
        save_to_data (bool): True ise data/ klasörüne kaydeder, False ise geçici dosya oluşturur.
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

        # Ses dosyasını kaydet
        if save_to_data and question_number is not None:
            # data/ klasörüne kaydet
            data_dir = "data"
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            audio_file = os.path.join(data_dir, f"soru-sesi-{question_number}.wav")
            with open(audio_file, 'wb') as f:
                f.write(response.audio_content)
            print(f"Soru sesi kaydedildi: {audio_file}")
        else:
            # Geçici dosya oluştur
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(response.audio_content)
                audio_file = temp_file.name

        # Sesi oynatmak için PyAudio'yu kullan
        print("Yanıt oynatılıyor...")
        p = pyaudio.PyAudio()
        stream = None
        
        try:
            with wave.open(audio_file, 'rb') as wf:
                stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                                channels=wf.getnchannels(),
                                rate=wf.getframerate(),
                                output=True)

                data = wf.readframes(1024)
                while data:
                    stream.write(data)
                    data = wf.readframes(1024)
                
                # Stream'i hemen kapat
                stream.stop_stream()
                stream.close()
        except Exception as e:
            print(f"Oynatma hatası: {e}")
        finally:
            # PyAudio'yu kapat
            try:
                p.terminate()
            except:
                pass
        
        # Oynatma bittikten sonra kısa bekleme
        import time
        time.sleep(0.5)  # Kısa bekleme
        
        # Sadece geçici dosyaları sil (data/ klasöründeki dosyalar kalır)
        if not save_to_data:
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
                    print("Geçici ses dosyası silindi")
            except Exception as e:
                print(f"Dosya silme hatası: {e}")

    except Exception as e:
        print(f"TTS API hatası: {e}")
        return None
    
    return audio_file if save_to_data else None