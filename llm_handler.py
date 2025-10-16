#



import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_interview_question(topic):
    try:
        # Yeni nesil model (Gemini 2.5)
        model = genai.GenerativeModel("models/gemini-2.5-pro")

        prompt = (
            f"Sen bir bilgisayar mühendisliği mülakat uzmanısın. "
            f"Lütfen mülakata yönelik, Türkçe olarak, sadece bir tane soru sor. "
            f"Soru, mühendislik alanında ve özellikle '{topic}' konusuyla ilgili olsun. "
            f"Sadece soruyu yaz, açıklama yapma. Yanıtlara örnek verme."
        )

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print(f"Gemini API hatası: {e}")
        return "Üzgünüm, şu anda bir soru üretemiyorum."

if __name__ == "__main__":
    topic = "Nesne Yönelimli Programlama"
    question = get_interview_question(topic)
    print(f"Üretilen mülakat sorusu: {question}")
