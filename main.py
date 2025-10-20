# main.py
from llm_handler import InterviewHandler
import random

def run_interview():
    ih = InterviewHandler(question_dir="question_pool")
    # Basit başlangıç: kişisel kategorisinden 1 soru al (varsa)
    personal_questions = [q for q in ih.questions if q.get("kategori") == "kişisel"]
    if not personal_questions:
        raise SystemExit("Kişisel sorular bulunamadı. data/question_pool içinde json'leri kontrol et.")
    # 1. soru: rastgele kişisel
    current_q = random.choice(personal_questions)

    total_turns = 8
    for turn in range(1, total_turns + 1):
        print(f"\nSoru {turn}: {current_q['soru']}")
        user_answer = input("Cevabınız: ").strip()

        # Gemini ile analiz
        analysis = ih.analyze_answer_with_gemini(user_answer, current_q.get("anahtar_kelimeler", []))
        print("\n--- Değerlendirme ---")
        print(analysis.get("feedback", analysis))
        print("Puan:", analysis.get("score"))

        # Kaydet
        ih.record_turn(current_q, user_answer, analysis)

        # Eğer son 2 soruya geldiysek (örn. 7 veya 8), senaryo üret
        if turn == 7:
            scenario = ih.generate_personal_scenario()
            print("\nSenaryo sorusu (kişiselleştirilmiş):")
            print(scenario.get("scenario"))
            # kullanıcıdan cevap al
            ans = input("Cevabınız: ")
            a = ih.analyze_answer_with_gemini(ans, [])
            ih.record_turn({"id": "SCENARIO", "soru": scenario.get("scenario"), "difficulty_level": 3}, ans, a)
            # Son takip sorusu
            print("\nTakip sorusu:")
            print(scenario.get("follow_up"))
            ans2 = input("Cevabınız: ")
            a2 = ih.analyze_answer_with_gemini(ans2, [])
            ih.record_turn({"id": "SCENARIO_FOLLOW", "soru": scenario.get("follow_up"), "difficulty_level": 3}, ans2, a2)
            break

        # Normal akış: bir sonraki soru seç
        next_q = ih.select_next_question(current_q.get("id"), user_answer)

        # Güvenlik: aynı soruyu tekrar sormamak için en fazla 10 tekrar dene
        attempts = 0
        while next_q["id"] in {h["id"] for h in ih.history} and attempts < 10:
            next_q = ih.select_next_question(current_q.get("id"), user_answer)
            attempts += 1

        current_q = next_q

    print("\nMülakat tamamlandı. Teşekkürler!")

if __name__ == "__main__":
    run_interview()
