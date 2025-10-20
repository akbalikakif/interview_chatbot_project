# main.py
from llm_handler import InterviewHandler
from text_to_speech import text_to_speech_playback
from speech_to_text import record_and_convert
import random

def run_interview():
    ih = InterviewHandler(question_dir="question_pool")
    # Test: teknik aşamalardan başla
    ih.current_phase = "teknik1"
    
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
        # Soruyu seslendir
        try:
            text_to_speech_playback(current_q['soru'])
        except Exception as e:
            print(f"TTS oynatma hatası: {e}")
        # Debug: zorluk düzeyi göster
        try:
            print(f"Zorluk: {current_q.get('difficulty_level', 'N/A')}")
        except Exception:
            pass
        
        # Kullanıcıdan sesli cevap al (Google STT)
        print("Cevabınızı mikrofona söyleyin...")
        stt_result = None
        try:
            stt_result = record_and_convert()
        except Exception as e:
            print(f"STT hatası: {e}")
            stt_result = None

        if stt_result and stt_result.get('transcript'):
            user_answer = stt_result['transcript']
            print(f"Algılanan cevap: {user_answer}")
        else:
            # STT başarısızsa güvenli geri dönüş: kısa varsayılan cevap
            user_answer = "Cevap algılanamadı; lütfen tekrar sorunuz."
            print("STT başarısız, varsayılan cevap kullanılacak.")

        # Gemini ile analiz
        analysis = ih.analyze_answer_with_gemini(user_answer, current_q.get("anahtar_kelimeler", []))
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
    
    # Özet rapor
    print("\n--- Mülakat Özeti ---")
    for i, h in enumerate(ih.history, 1):
        print(f"{i}. {h.get('kategori', 'Bilinmeyen')} - Puan: {h.get('analysis', {}).get('score', 'N/A')}")

if __name__ == "__main__":
    run_interview()
