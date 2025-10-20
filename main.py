# main.py
from llm_handler import InterviewHandler
from text_to_speech import text_to_speech_playback
from speech_to_text import record_and_convert
from analysis_handler import AnalysisHandler
from reports import generate_final_report
import random
import os
import shutil
import warnings
warnings.filterwarnings("ignore")

def run_interview():
    ih = InterviewHandler(question_dir="question_pool")
    # Doğru akış: kişisel sorulardan başla
    ih.current_phase = "kişisel"
    
    # data klasörünü oluştur
    if not os.path.exists("data"):
        os.makedirs("data")
    
    # Ses analizi handler'ını başlat
    audio_analyzer = AnalysisHandler()
    
    print("=== Akıllı Mülakat Sistemi ===")
    print("Mülakat akışı:")
    print("1. Kişisel soru (bağımsız)")
    print("2. Kişisel soru (bağımsız)")
    print("3. Teknik soru (bağımsız)")
    print("4. Teknik soru (3. soruya bağlı)")
    print("5. Teknik soru (bağımsız)")
    print("6. Teknik soru (5. soruya bağlı)")
    print("7. Senaryo sorusu (kişiselleştirilmiş)")
    print("8. Senaryo takip sorusu")
    print("\nMülakat başlıyor...\n")

    total_turns = 8
    for turn in range(1, total_turns + 1):
        # Akıllı akışa göre soru seç
        current_q = ih.get_next_question_by_phase()
        print(f"\n=== Soru {turn} ({ih.current_phase.upper()}) ===")
        print(f"Soru: {current_q['soru']}")
        # Soruyu seslendir ve data/ klasörüne kaydet
        try:
            text_to_speech_playback(current_q['soru'], question_number=turn, save_to_data=True)
        except Exception as e:
            print(f"TTS oynatma hatası: {e}")
        # Debug: zorluk düzeyi göster
        try:
            print(f"Zorluk: {current_q.get('difficulty_level', 'N/A')}")
        except Exception:
            pass
        
        # Kullanıcıdan sesli cevap al (Google STT) ve data/ klasörüne kaydet
        print("Cevabınızı mikrofona söyleyin...")
        stt_result = None
        try:
            stt_result = record_and_convert(question_number=turn)
        except Exception as e:
            print(f"STT hatası: {e}")
            stt_result = None

        # Ses analizi değişkenlerini başlat
        audio_analysis = None
        overall_audio_score = None
        
        if stt_result and stt_result.get('transcript'):
            user_answer = stt_result['transcript']
            print(f"Algılanan cevap: {user_answer}")
            
            # Ses dosyası analizi (eğer dosya varsa)
            audio_file_path = stt_result.get('audio_file')
            if audio_file_path and os.path.exists(audio_file_path):
                print("Ses dosyası analizi yapılıyor...")
                try:
                    # Ses dosyasını analiz et
                    audio_metrics = audio_analyzer.analyze_audio_file(audio_file_path)
                    
                    # Metin analizi yap
                    text_metrics = audio_analyzer.analyze_text_for_fillers(user_answer)
                    
                    # Genel skor hesapla (ses + metin)
                    overall_audio_score = audio_analyzer.calculate_overall_score(audio_metrics, text_metrics)
                    
                    print(f"Ses analizi tamamlandı - Genel skor: {overall_audio_score['overall_score']}/100")
                except Exception as e:
                    print(f"Ses analizi hatası: {e}")
                    # Hata durumunda sadece metin analizi yap
                    try:
                        text_analysis = audio_analyzer.analyze_text_for_fillers(user_answer)
                        overall_audio_score = {
                            'overall_score': text_analysis['filler_score'],
                            'scores': {
                                'akıcılık': text_analysis['filler_score'],
                                'konuşma_hızı': 80,
                                'ses_tonu': 80
                            },
                            'confidence_level': 'metin-bazlı'
                        }
                    except Exception as e2:
                        print(f"Metin analizi hatası: {e2}")
                        overall_audio_score = None
            else:
                # Ses dosyası yoksa sadece metin analizi
                print("Metin analizi yapılıyor...")
                try:
                    text_analysis = audio_analyzer.analyze_text_for_fillers(user_answer)
                    overall_audio_score = {
                        'overall_score': text_analysis['filler_score'],
                        'scores': {
                            'akıcılık': text_analysis['filler_score'],
                            'konuşma_hızı': 80,
                            'ses_tonu': 80
                        },
                        'confidence_level': 'metin-bazlı'
                    }
                    print(f"Metin analizi tamamlandı - Genel skor: {overall_audio_score['overall_score']}/100")
                except Exception as e:
                    print(f"Metin analizi hatası: {e}")
                    overall_audio_score = None
        else:
            # STT başarısızsa güvenli geri dönüş: kısa varsayılan cevap
            user_answer = "Cevap algılanamadı; lütfen tekrar sorunuz."
            print("STT başarısız, varsayılan cevap kullanılacak.")

        # Gemini ile analiz (ses puanlarını da dahil et)
        reference_keys = current_q.get("anahtar_kelimeler", [])
        
        # Ses analizi varsa LLM'e gönder
        if overall_audio_score:
            audio_context = f"""
Ses Analizi Sonuçları:
- Genel ses skoru: {overall_audio_score['overall_score']}/100
- Akıcılık: {overall_audio_score['scores']['akıcılık']}/100
- Konuşma hızı: {overall_audio_score['scores']['konuşma_hızı']}/100
- Ses tonu: {overall_audio_score['scores']['ses_tonu']}/100
- Güvenilirlik: {overall_audio_score['confidence_level']}
"""
            enhanced_answer = f"{user_answer}\n\n{audio_context}"
        else:
            enhanced_answer = user_answer
            
        analysis = ih.analyze_answer_with_gemini(enhanced_answer, reference_keys)
        print("\n--- Değerlendirme ---")
        print(analysis.get("feedback", analysis))
        print("Puan:", analysis.get("score"))

        # Kaydet (bu otomatik olarak fazı ilerletir)
        ih.record_turn(current_q, user_answer, analysis)

        # Mülakat tamamlandı mı kontrol et
        if ih.current_phase == "tamamlandı":
            break

    print("\n=== Mülakat Tamamlandı ===")
    print("Teşekkürler! Değerlendirme raporu hazırlanıyor...")
    
    # Detaylı rapor oluştur
    try:
        report = generate_final_report(ih)
        print("\n" + "="*50)
        print("DETAYLI RAPOR")
        print("="*50)
        print(report)
    except Exception as e:
        print(f"Rapor oluşturma hatası: {e}")
    
    # Özet rapor
    print("\n--- Mülakat Özeti ---")
    for i, h in enumerate(ih.history, 1):
        print(f"{i}. {h.get('kategori', 'Bilinmeyen')} - Puan: {h.get('analysis', {}).get('score', 'N/A')}")
    
    # Tüm ses dosyalarını temizle (soru-1.wav, soru-2.wav, soru-sesi-1.wav, vb.)
    print("\n--- Ses Dosyaları Temizleniyor ---")
    try:
        if os.path.exists("data"):
            for filename in os.listdir("data"):
                if filename.endswith(".wav"):
                    file_path = os.path.join("data", filename)
                    try:
                        os.remove(file_path)
                        print(f"Silindi: {filename}")
                    except Exception as e:
                        print(f"{filename} silinirken hata: {e}")
            
            print("Tüm ses dosyaları temizlendi.")
        else:
            print("data/ klasörü bulunamadı.")
    except Exception as e:
        print(f"Ses dosyası temizleme hatası: {e}")

if __name__ == "__main__":
    run_interview()
