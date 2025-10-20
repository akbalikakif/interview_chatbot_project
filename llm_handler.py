#.



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
    """
llm_handler.py
InterviewHandler: soru havuzu okuma, cevap analizi (Gemini), bağlamlı soru seçimi,
fallback ve senaryo üretimi mantığını içerir.
"""

import os
import json
import random 
import google.generativeai as genai
from typing import List, Dict, Optional
from dotenv import load_dotenv



load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY .env içinde bulunamadı")
genai.configure(api_key=API_KEY)

class InterviewHandler:
    def __init__(self, question_dir: str = "data/question_pool"):
        """
        - question_dir altındaki tüm .json dosyalarını yükler.
        - questions: list of dict (her dict soruyu temsil eder)
        """
        self.questions: List[Dict] = self._load_questions(question_dir)
        self.history: List[Dict] = [] 

    def _load_questions(self, question_dir: str) -> List[Dict]:
        out = []
        for fn in sorted(os.listdir(question_dir)):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(question_dir, fn)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    out.extend(data)
        return out

    def get_question_by_id(self, qid: str) -> Optional[Dict]:
        return next((q for q in self.questions if q.get("id") == qid), None)


    def keyword_match(self, answer: str, question: Dict) -> bool:
       
        text = (answer or "").lower()
      
        for kw in question.get("anahtar_kelimeler", []):
            if kw.lower() in text:
                return True

        for tag in question.get("etiketler", []):
            if tag.lower() in text:
                return True
        return False


    def find_questions_by_answer_tags(self, answer: str) -> List[Dict]:
        
        candidates = []
        text = (answer or "").lower()
        for q in self.questions:
            # ignore very trivial matches by requiring whole-word or substring match
            found = False
            for kw in q.get("anahtar_kelimeler", []) + q.get("etiketler", []):
                if kw and kw.lower() in text:
                    found = True
                    break
            if found:
                candidates.append(q)
        return candidates


    def analyze_answer_with_gemini(self, answer: str, reference_keys: List[str]) -> Dict:
      
        if not API_KEY:
            return {"score": None, "found": [], "feedback": "API key yok, lokal değerlendirme yapıldı."}

        model = genai.GenerativeModel("gemini-1.5") 
        prompt = f"""
You are an assistant that evaluates interview answers against reference keywords.
Answer in JSON with keys: found_keywords (list), score (0-10 integer), feedback (short).

Answer to evaluate:
\"\"\"{answer}\"\"\"

Reference keywords:
{reference_keys}
"""
      
        resp = model.generate_content(prompt=prompt, max_output_tokens=250)

        text = getattr(resp, "text", "") or ""
        try:
           
            import re, json as _json
          
            m = re.search(r"(\{.*\})", text, re.DOTALL)
            if m:
                parsed = _json.loads(m.group(1))
                return parsed
            else:
                return {"score": None, "found_keywords": [], "feedback": text.strip()}
        except Exception:
            return {"score": None, "found_keywords": [], "feedback": text.strip()}


    def select_next_question(self, current_qid: str, user_answer: str) -> Dict:
        """
        Adımlar:
        1) Kullanıcının cevabından etiket/anahtar kelime eşleşmesi ara (havuz geneli).
        2) Eşleşme varsa uygun zorluk/durum filtresiyle bir candidate seç.
        3) Eşleşme yoksa current question'ın fallback_id'sini dene.
        4) Hâlâ yoksa rastgele ve history'ye bakarak tekrar sorulmayan bir soru seç.
        Ayrıca: prereq_tags ve follow_up_to kurallarını da gözetir.
        """
        current_q = self.get_question_by_id(current_qid)
      
        candidates = self.find_questions_by_answer_tags(user_answer)

        preferred = []
        if current_q and current_q.get("difficulty_level") is not None:
            d = current_q["difficulty_level"]
            preferred = [q for q in candidates if q.get("difficulty_level") == d]
        if not preferred:
            preferred = candidates

        
        asked_ids = {h["id"] for h in self.history}
        preferred = [q for q in preferred if q["id"] not in asked_ids]

   
        if preferred:
            return random.choice(preferred)

     
        if current_q:
            fallback_id = current_q.get("fallback_id")
            if fallback_id:
                fb = self.get_question_by_id(fallback_id)
                if fb and fb["id"] not in asked_ids:
                    return fb

        followups = [q for q in self.questions if q.get("follow_up_to") == current_qid and q["id"] not in asked_ids]
        if followups:
            return random.choice(followups)

        if current_q:
            same_diff = [q for q in self.questions if q.get("difficulty_level") == current_q.get("difficulty_level") and q["id"] not in asked_ids]
            if same_diff:
                return random.choice(same_diff)

        remaining = [q for q in self.questions if q["id"] not in asked_ids]
        if remaining:
            return random.choice(remaining)

        return random.choice(self.questions)

   
    def record_turn(self, question: Dict, answer: str, analysis: Dict):
        self.history.append({
            "id": question["id"],
            "soru": question.get("soru"),
            "answer": answer,
            "analysis": analysis,
            "difficulty": question.get("difficulty_level")
        })

    def generate_personal_scenario(self) -> Dict:
        """
        Tarihçedeki cevaplardan kısa bir özet çıkarıp Gemini'den
        kişiselleştirilmiş bir senaryo (ve takip sorusu) üretmesini ister.
        Döndürülen yapı: {"scenario": str, "follow_up": str}
        """
       
        last_answers = [h["answer"] for h in self.history[-6:]]
        summary = "\n".join(f"- {a}" for a in last_answers)
        prompt = f"""
You are a helpful interviewer AI. Given these candidate answers:
{summary}

Create:
1) A concise personalized scenario-based question that fits the candidate (1-2 sentences).
2) A follow-up question that digs deeper into the candidate's decision.

Return JSON: {{ "scenario": "...", "follow_up": "..." }}
"""
        model = genai.GenerativeModel("gemini-1.5")
        resp = model.generate_content(prompt=prompt, max_output_tokens=250)
        text = getattr(resp, "text", "") or ""
        try:
            import re, json as _json
            m = re.search(r"(\{.*\})", text, re.DOTALL)
            if m:
                return _json.loads(m.group(1))
            else:
                return {"scenario": text.strip(), "follow_up": ""}
        except Exception:
            return {"scenario": text.strip(), "follow_up": ""}


