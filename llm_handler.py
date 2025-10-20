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
    print("UYARI: GEMINI_API_KEY .env içinde bulunamadı. Test modu aktif.")
    API_KEY = "test_key"  # Test için geçici key
genai.configure(api_key=API_KEY)

class InterviewHandler:
    def __init__(self, question_dir: str = "question_pool"):
        """
        - question_dir altındaki tüm .json dosyalarını yükler.
        - questions: list of dict (her dict soruyu temsil eder)
        """
        self.questions: List[Dict] = self._load_questions(question_dir)
        self.history: List[Dict] = [] 
        self.current_phase = "kişisel"  # kişisel -> teknik1 -> teknik2 -> senaryo -> takip
        self.phase_questions_asked = 0 
        self.last_scenario: Optional[Dict] = None
        # Seçim sırasında kullanacağımız hedef zorluk default değerleri
        self.default_difficulty_by_phase = {
            "teknik1": 1,
            "teknik2": 1,
            "teknik3": 2,
            "teknik4": 2,
        }

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

    def _collect_satisfied_tags(self) -> set:
        """Geçmiş cevaplardan çıkarılan etiket/anahtar kelime benzeri tatmin edilmiş konular.
        - analysis.found_keywords
        - cevap kelimeleri (basit alt string yaklaşımı için token seti)"""
        satisfied = set()
        for h in self.history:
            ans = (h.get("answer") or "").lower()
            for token in ans.split():
                if token:
                    satisfied.add(token.strip(".,;:!?()[]{}"))
            fk = (h.get("analysis") or {}).get("found_keywords") or []
            for kw in fk:
                if kw:
                    satisfied.add(str(kw).lower())
        return satisfied

    def _filter_by_prereqs(self, candidates: List[Dict]) -> List[Dict]:
        """prereq_tags alanı, önceki yanıtlarda tatmin edilmiş olmalı."""
        if not candidates:
            return candidates
        satisfied = self._collect_satisfied_tags()
        filtered = []
        for q in candidates:
            prereqs = [str(t).lower() for t in q.get("prereq_tags", [])]
            if all((p in satisfied) for p in prereqs):
                filtered.append(q)
        return filtered or candidates  # hiçbiri kalmazsa, orijinal listeyi kullan (yumuşak kısıt)

    def _choose_by_difficulty(self, candidates: List[Dict], target: Optional[int]) -> Optional[Dict]:
        """Hedef zorluğa en yakın soruyu seç. Hedef yoksa rastgele."""
        if not candidates:
            return None
        if target is None:
            return random.choice(candidates)
        def dist(q):
            try:
                return abs((q.get("difficulty_level") or 1) - target)
            except Exception:
                return 999
        best_dist = min(dist(q) for q in candidates)
        best = [q for q in candidates if dist(q) == best_dist]
        return random.choice(best)

    def _target_difficulty_from_last(self, fallback_phase_key: str) -> int:
        """Son teknik cevabın skoruna göre zorluğu ayarla."""
        # Varsayılan
        target = self.default_difficulty_by_phase.get(fallback_phase_key, 1)
        # Son teknik turu bul
        last = None
        for h in reversed(self.history):
            if h.get("kategori") == "teknik":
                last = h
                break
        if not last:
            return target
        last_score = ((last.get("analysis") or {}).get("score"))
        last_diff = last.get("difficulty") or 1
        if isinstance(last_score, (int, float)):
            if last_score >= 6:
                target = min(3, last_diff + 1)
            elif last_score <= 3:
                target = max(1, last_diff - 1)
            else:
                target = last_diff
        return target


    def analyze_answer_with_gemini(self, answer: str, reference_keys: List[str]) -> Dict:
      
        if not API_KEY:
            # Test modu için basit değerlendirme
            score = min(10, len(answer.split()) // 3)  # Kelime sayısına göre basit puan
            return {
                "score": score, 
                "found_keywords": reference_keys[:2] if reference_keys else [], 
                "feedback": f"Test modu - Cevap uzunluğu: {len(answer)} karakter. Puan: {score}/10"
            }

        try:
            model = genai.GenerativeModel("gemini-2.5-pro")
        except Exception as e:
            print(f"Model hatası: {e}")
            # API hatası durumunda test modu
            score = min(10, len(answer.split()) // 3)
            return {
                "score": score, 
                "found_keywords": reference_keys[:2] if reference_keys else [], 
                "feedback": f"API hatası - Test modu. Puan: {score}/10"
            }
        # Gerçek değerlendirme
        prompt = f"""Rate this interview answer from 1-10 and give feedback.

Answer: {answer}
Keywords to check: {reference_keys}

Respond with JSON: {{"score": 8, "feedback": "Good technical knowledge"}}"""
        
        resp = model.generate_content(prompt)

        try:
            text = resp.text
        except ValueError as e:
            print(f"Response hatası: {e}")
            return {"score": 5, "found_keywords": [], "feedback": "API response hatası - varsayılan puan verildi"}
        
        try:
            import re, json as _json
            # JSON formatını bul
            m = re.search(r"(\{.*\})", text, re.DOTALL)
            if m:
                parsed = _json.loads(m.group(1))
                return parsed
            else:
                # Eğer JSON yoksa, sadece sayıyı çıkar
                score_match = re.search(r'\b(\d+)\b', text)
                if score_match:
                    score = int(score_match.group(1))
                    return {"score": score, "found_keywords": [], "feedback": f"Puan: {score}/10"}
                else:
                    return {"score": 5, "found_keywords": [], "feedback": text.strip()}
        except Exception as e:
            print(f"Parse hatası: {e}")
            return {"score": 5, "found_keywords": [], "feedback": text.strip()}


    def get_next_question_by_phase(self) -> Dict:
        """
        Akıllı mülakat akışına göre bir sonraki soruyu seçer:
        1. Kişisel soru (bağımsız)
        2. Kişisel soru (bağımsız) 
        3. Teknik soru (bağımsız)
        4. Teknik soru (3. soruya bağlı)
        5. Teknik soru (bağımsız)
        6. Teknik soru (5. soruya bağlı)
        7. Senaryo sorusu (kişiselleştirilmiş)
        8. Senaryo takip sorusu (7. soruya bağlı)
        """
        asked_ids = {h["id"] for h in self.history}
        
        if self.current_phase == "kişisel":
            # Kişisel sorular (bağımsız)
            candidates = [q for q in self.questions 
                        if q.get("kategori") == "kişisel" 
                        and q.get("follow_up_to") is None
                        and q["id"] not in asked_ids]
            candidates = self._filter_by_prereqs(candidates)
            if candidates:
                return random.choice(candidates)
            else:
                # Fallback: herhangi bir kişisel soru
                candidates = [q for q in self.questions 
                            if q.get("kategori") == "kişisel" 
                            and q["id"] not in asked_ids]
                candidates = self._filter_by_prereqs(candidates)
                if candidates:
                    return random.choice(candidates)
        
        elif self.current_phase == "teknik1":
            # Teknik soru (bağımsız)
            candidates = [q for q in self.questions 
                        if q.get("kategori") == "teknik" 
                        and q.get("follow_up_to") is None
                        and q["id"] not in asked_ids]
            candidates = self._filter_by_prereqs(candidates)
            target = self.default_difficulty_by_phase.get("teknik1")
            pick = self._choose_by_difficulty(candidates, target)
            if pick:
                return pick
            else:
                # Fallback: herhangi bir teknik soru
                candidates = [q for q in self.questions 
                            if q.get("kategori") == "teknik" 
                            and q["id"] not in asked_ids]
                candidates = self._filter_by_prereqs(candidates)
                pick = self._choose_by_difficulty(candidates, target)
                if pick:
                    return pick
        
        elif self.current_phase == "teknik2":
            # Teknik soru (3. soruya bağlı)
            last_technical = None
            for h in reversed(self.history):
                if h.get("kategori") == "teknik":
                    last_technical = h
                    break

            if last_technical:
                # 1) follow_up_to bağıyla doğrudan bağlı soru varsa onu seç
                direct_followups = [q for q in self.questions
                                    if q.get("kategori") == "teknik"
                                    and q.get("follow_up_to") == last_technical.get("id")
                                    and q["id"] not in asked_ids]
                if direct_followups:
                    direct_followups = self._filter_by_prereqs(direct_followups)
                    target = self._target_difficulty_from_last("teknik2")
                    pick = self._choose_by_difficulty(direct_followups, target)
                    if pick:
                        return pick

                # 2) Etikete/anahtar kelimeye göre bağlamlı soru bulmayı dene
                candidates = self.find_questions_by_answer_tags(last_technical.get("answer", ""))
                candidates = [q for q in candidates
                              if q.get("kategori") == "teknik"
                              and q["id"] not in asked_ids]
                if candidates:
                    candidates = self._filter_by_prereqs(candidates)
                    target = self._target_difficulty_from_last("teknik2")
                    pick = self._choose_by_difficulty(candidates, target)
                    if pick:
                        return pick

                # 3) Fallback_id tanımlıysa, o soruyu sor
                fallback_id = None
                try:
                    # last_technical, history öğesidir; orijinal soru özelliklerini taşımıyor olabilir
                    # Bu yüzden soru havuzundan id ile bulalım
                    original_q = self.get_question_by_id(last_technical.get("id"))
                    if original_q:
                        fallback_id = original_q.get("fallback_id")
                except Exception:
                    fallback_id = None

            if fallback_id:
                fb = self.get_question_by_id(fallback_id)
                if fb and fb.get("kategori") == "teknik" and fb["id"] not in asked_ids:
                        fb_cands = self._filter_by_prereqs([fb])
                        target = self._target_difficulty_from_last("teknik2")
                        pick = self._choose_by_difficulty(fb_cands, target)
                        if pick:
                            return pick

            # 4) Son çare: bağımsız teknik soru
            candidates = [q for q in self.questions
                          if q.get("kategori") == "teknik"
                          and q.get("follow_up_to") is None
                          and q["id"] not in asked_ids]
            candidates = self._filter_by_prereqs(candidates)
            target = self._target_difficulty_from_last("teknik2")
            pick = self._choose_by_difficulty(candidates, target)
            if pick:
                return pick
        
        elif self.current_phase == "teknik3":
            # Teknik soru (bağımsız)
            candidates = [q for q in self.questions 
                        if q.get("kategori") == "teknik" 
                        and q.get("follow_up_to") is None
                        and q["id"] not in asked_ids]
            candidates = self._filter_by_prereqs(candidates)
            target = self._target_difficulty_from_last("teknik3")
            pick = self._choose_by_difficulty(candidates, target)
            if pick:
                return pick
        
        elif self.current_phase == "teknik4":
            # Teknik soru (5. soruya bağlı)
            last_technical = None
            for h in reversed(self.history):
                if h.get("kategori") == "teknik":
                    last_technical = h
                    break

            if last_technical:
                # 1) follow_up_to bağıyla doğrudan bağlı soru
                direct_followups = [q for q in self.questions
                                    if q.get("kategori") == "teknik"
                                    and q.get("follow_up_to") == last_technical.get("id")
                                    and q["id"] not in asked_ids]
                if direct_followups:
                    direct_followups = self._filter_by_prereqs(direct_followups)
                    target = self._target_difficulty_from_last("teknik4")
                    pick = self._choose_by_difficulty(direct_followups, target)
                    if pick:
                        return pick

                # 2) Etiket/anahtar kelimeye göre bağlamlı soru
                candidates = self.find_questions_by_answer_tags(last_technical.get("answer", ""))
                candidates = [q for q in candidates
                              if q.get("kategori") == "teknik"
                              and q["id"] not in asked_ids]
                if candidates:
                    candidates = self._filter_by_prereqs(candidates)
                    target = self._target_difficulty_from_last("teknik4")
                    pick = self._choose_by_difficulty(candidates, target)
                    if pick:
                        return pick

                # 3) fallback_id varsa kullan
                fallback_id = None
                try:
                    original_q = self.get_question_by_id(last_technical.get("id"))
                    if original_q:
                        fallback_id = original_q.get("fallback_id")
                except Exception:
                    fallback_id = None

                if fallback_id:
                    fb = self.get_question_by_id(fallback_id)
                    if fb and fb.get("kategori") == "teknik" and fb["id"] not in asked_ids:
                        fb_cands = self._filter_by_prereqs([fb])
                        target = self._target_difficulty_from_last("teknik4")
                        pick = self._choose_by_difficulty(fb_cands, target)
                        if pick:
                            return pick

            # 4) Son çare: bağımsız teknik soru
            candidates = [q for q in self.questions 
                          if q.get("kategori") == "teknik"
                          and q.get("follow_up_to") is None
                          and q["id"] not in asked_ids]
            candidates = self._filter_by_prereqs(candidates)
            target = self._target_difficulty_from_last("teknik4")
            pick = self._choose_by_difficulty(candidates, target)
            if pick:
                return pick
        
        elif self.current_phase == "senaryo":
            # Senaryo sorusu (kişiselleştirilmiş)
            scenario = self.generate_personal_scenario()
            self.last_scenario = scenario or {}
            return {
                "id": "SCENARIO",
                "kategori": "senaryo",
                "soru": scenario.get("scenario", "Kişiselleştirilmiş senaryo sorusu"),
                "difficulty_level": 3,
                "etiketler": ["senaryo"],
                "prereq_tags": [],
                "follow_up_to": None,
                "cevap_ornegi": "free_talk",
                "anahtar_kelimeler": [],
                "puanlama_kriteri": "mantik-tutarliligi",
                "fallback_id": None
            }
        
        elif self.current_phase == "takip":
            # Senaryo takip sorusu
            follow_text = None
            if isinstance(getattr(self, "last_scenario", None), dict):
                follow_text = self.last_scenario.get("follow_up")
            return {
                "id": "SCENARIO_FOLLOW",
                "kategori": "senaryo",
                "soru": follow_text or "Aldığın kararı ekip kabul etmedi. Bu durumda nasıl ilerlerdin?",
                "difficulty_level": 3,
                "etiketler": ["senaryo", "takip"],
                "prereq_tags": [],
                "follow_up_to": "SCENARIO",
                "cevap_ornegi": "free_talk",
                "anahtar_kelimeler": [],
                "puanlama_kriteri": "mantik-tutarliligi",
                "fallback_id": None
            }
        
        # Son çare: herhangi bir soru
        remaining = [q for q in self.questions if q["id"] not in asked_ids]
        if remaining:
            return random.choice(remaining)

        return random.choice(self.questions)

    def advance_phase(self):
        """Mülakat fazını ilerletir"""
        # Soru sayısına göre faz belirle
        question_count = len(self.history)
        
        if question_count == 0:
            self.current_phase = "kişisel"
        elif question_count == 1:
            self.current_phase = "kişisel"  # 2. kişisel soru
        elif question_count == 2:
            self.current_phase = "teknik1"  # 1. teknik soru
        elif question_count == 3:
            self.current_phase = "teknik2"  # 2. teknik soru (bağlı)
        elif question_count == 4:
            self.current_phase = "teknik3"  # 3. teknik soru
        elif question_count == 5:
            self.current_phase = "teknik4"  # 4. teknik soru (bağlı)
        elif question_count == 6:
            self.current_phase = "senaryo"  # Senaryo sorusu
        elif question_count == 7:
            self.current_phase = "takip"    # Takip sorusu
        else:
            self.current_phase = "tamamlandı"

    def select_next_question(self, current_qid: str, user_answer: str) -> Dict:
        """
        Eski metod - geriye dönük uyumluluk için korundu
        Yeni akıllı akış için get_next_question_by_phase() kullanın
        """
        return self.get_next_question_by_phase()

   
    def record_turn(self, question: Dict, answer: str, analysis: Dict):
        self.history.append({
            "id": question["id"],
            "kategori": question.get("kategori"),
            "soru": question.get("soru"),
            "answer": answer,
            "analysis": analysis,
            "difficulty": question.get("difficulty_level")
        })
        
        # Fazı ilerlet
        self.advance_phase()

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

IMPORTANT: Return ONLY valid JSON in this exact format:
{{"scenario": "Your scenario question here", "follow_up": "Your follow-up question here"}}
"""
        model = genai.GenerativeModel("gemini-2.5-pro")
        resp = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(max_output_tokens=250))
        
        try:
            text = resp.text
            print(f"DEBUG: Gemini senaryo cevabı: {text}")
        except ValueError as e:
            print(f"Scenario response hatası: {e}")
            return {"scenario": "Kişiselleştirilmiş senaryo sorusu", "follow_up": "Bu durumda nasıl ilerlerdin?"}
        
        try:
            import json as _json
            # Önce direkt JSON parse dene
            try:
                return _json.loads(text.strip())
            except:
                # JSON bulmaya çalış
                import re
                m = re.search(r'\{[^{}]*"scenario"[^{}]*"follow_up"[^{}]*\}', text, re.DOTALL)
                if m:
                    return _json.loads(m.group(0))
                else:
                    # Son çare: metni böl
                    lines = text.strip().split('\n')
                    scenario = "Kişiselleştirilmiş senaryo sorusu"
                    follow_up = "Bu durumda nasıl ilerlerdin?"
                    
                    for line in lines:
                        if 'scenario' in line.lower():
                            scenario = line.split(':', 1)[-1].strip().strip('"')
                        elif 'follow' in line.lower():
                            follow_up = line.split(':', 1)[-1].strip().strip('"')
                    
                    return {"scenario": scenario, "follow_up": follow_up}
        except Exception as e:
            print(f"Scenario JSON parse hatası: {e}")
            return {"scenario": "Kişiselleştirilmiş senaryo sorusu", "follow_up": "Bu durumda nasıl ilerlerdin?"}


