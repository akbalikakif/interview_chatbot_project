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
    def __init__(self, question_dir: str = "question_pool", cv_tags: List[str] = None):
        """
        - question_dir altındaki tüm .json dosyalarını yükler.
        - questions: list of dict (her dict soruyu temsil eder)
        - cv_tags: CV'den çıkarılan etiketler (opsiyonel)
        """
        self.questions: List[Dict] = self._load_questions(question_dir)
        self.history: List[Dict] = [] 
        self.current_phase = "kişisel"  # kişisel -> teknik1 -> teknik2 -> senaryo -> takip
        self.phase_questions_asked = 0 
        self.last_scenario: Optional[Dict] = None
        self.cv_tags = cv_tags or []  # CV bazlı etiketler
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
        """
        Cevaptaki anahtar kelimelere ve etiketlere göre ilgili soruları bulur.
        Eşleşme skoruna göre sıralı döndürür.
        """
        candidates = []
        text = (answer or "").lower()
        
        # Cevaptaki kelimeleri tokenize et
        answer_tokens = set(text.split())
        
        for q in self.questions:
            match_score = 0
            
            # Anahtar kelime eşleşmeleri (daha yüksek ağırlık)
            for kw in q.get("anahtar_kelimeler", []):
                if kw and kw.lower() in text:
                    match_score += 3  # Anahtar kelime eşleşmesi
                    
            # Etiket eşleşmeleri
            for tag in q.get("etiketler", []):
                if tag and tag.lower() in text:
                    match_score += 2  # Etiket eşleşmesi
                # Etiket içindeki kelimeleri de kontrol et (örn: "nesne-tabanlı-programlama")
                tag_words = tag.lower().replace("-", " ").split()
                for tag_word in tag_words:
                    if tag_word in answer_tokens:
                        match_score += 1  # Kısmi etiket eşleşmesi
            
            if match_score > 0:
                candidates.append((q, match_score))
        
        # Eşleşme skoruna göre sırala (en yüksek önce)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Sadece soruları döndür (skorları değil)
        return [q for q, score in candidates]

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
        """Ön koşul kontrolü yapar"""
        out = []
        for q in candidates:
            prereqs = q.get("prereq_tags", [])
            if not prereqs:
                out.append(q)
                continue
            # Geçmiş cevaplarda bu etiketler var mı?
            all_tags = set()
            for h in self.history:
                all_tags.update(h.get("tags", []))
            if all(tag in all_tags for tag in prereqs):
                out.append(q)
        return out
    
    def _filter_by_cv_tags(self, candidates: List[Dict]) -> List[Dict]:
        """CV etiketlerine göre soruları filtrele - kısmi eşleşmeleri de kabul eder"""
        if not self.cv_tags:
            return candidates
        
        matched = []
        cv_tags_lower = [cv_tag.lower() for cv_tag in self.cv_tags]
        
        for q in candidates:
            # Soru JSON'unda 'etiketler' anahtarı kullanılıyor
            q_tags = q.get("etiketler", [])
            
            # Tam eşleşme veya kısmi eşleşme kontrolü
            for q_tag in q_tags:
                q_tag_lower = q_tag.lower()
                
                # 1. Tam eşleşme
                if q_tag_lower in cv_tags_lower:
                    matched.append(q)
                    break
                
                # 2. CV etiketi soru etiketinin içinde (örn: "python" in "nodejs-python-java")
                if any(cv_tag in q_tag_lower for cv_tag in cv_tags_lower):
                    matched.append(q)
                    break
                
                # 3. Soru etiketi CV etiketinin içinde (örn: "react" in "react-vue-angular")
                if any(q_tag_lower in cv_tag for cv_tag in cv_tags_lower):
                    matched.append(q)
                    break
        
        return matched if matched else candidates  # Eşleşme yoksa tüm adayları döndür

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
            # Teknik soru (bağımsız) - CV bazlı eşleştirme
            candidates = [q for q in self.questions 
                        if q.get("kategori") == "teknik" 
                        and q.get("follow_up_to") is None
                        and q["id"] not in asked_ids]
            candidates = self._filter_by_prereqs(candidates)
            
            # CV etiketlerine göre filtrele (varsa)
            if self.cv_tags:
                cv_matched = self._filter_by_cv_tags(candidates)
                if cv_matched:
                    candidates = cv_matched
                    print(f"   [CV EŞLEŞTİRME] {len(candidates)} soru CV'ye uygun")
            
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
                    print(f"   [ETİKET EŞLEŞTİRME] {len(candidates)} bağlamlı soru bulundu")
                    print(f"   Önceki cevap etiketleri: {last_technical.get('tags', [])}")
                    candidates = self._filter_by_prereqs(candidates)
                    target = self._target_difficulty_from_last("teknik2")
                    pick = self._choose_by_difficulty(candidates, target)
                    if pick:
                        print(f"   [BAĞLAMLI SORU] Seçilen: {pick.get('id')} - Etiketler: {pick.get('etiketler', [])}")
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
            # Teknik soru (bağımsız) - CV bazlı eşleştirme
            candidates = [q for q in self.questions 
                        if q.get("kategori") == "teknik" 
                        and q.get("follow_up_to") is None
                        and q["id"] not in asked_ids]
            candidates = self._filter_by_prereqs(candidates)
            
            # CV etiketlerine göre filtrele (varsa)
            if self.cv_tags:
                cv_matched = self._filter_by_cv_tags(candidates)
                if cv_matched:
                    candidates = cv_matched
                    print(f"   [CV EŞLEŞTİRME] {len(candidates)} soru CV'ye uygun")
            
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
                    print(f"   [ETİKET EŞLEŞTİRME] {len(candidates)} bağlamlı soru bulundu")
                    print(f"   Önceki cevap etiketleri: {last_technical.get('tags', [])}")
                    candidates = self._filter_by_prereqs(candidates)
                    target = self._target_difficulty_from_last("teknik4")
                    pick = self._choose_by_difficulty(candidates, target)
                    if pick:
                        print(f"   [BAĞLAMLI SORU] Seçilen: {pick.get('id')} - Etiketler: {pick.get('etiketler', [])}")
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
            # 7. Soru: Senaryo havuzundan seç (tutarlı, test edilmiş)
            asked_ids = {h["id"] for h in self.history}
            scenario_candidates = [q for q in self.questions 
                                  if q.get("kategori") == "senaryo" 
                                  and q["id"] not in asked_ids]
            
            if scenario_candidates:
                # Havuzdan rastgele seç
                scenario_q = random.choice(scenario_candidates)
                # Seçilen senaryoyu kaydet (8. soru için)
                self.last_scenario_question = scenario_q
                print(f"   [SENARYO] Havuzdan seçildi: {scenario_q['id']}", flush=True)
                return scenario_q
            else:
                # Fallback: LLM ile üret
                print(f"   [SENARYO] Havuzda soru kalmadı, LLM ile üretiliyor...", flush=True)
                scenario = self.generate_personal_scenario()
                self.last_scenario = scenario or {}
                return {
                    "id": "SCENARIO_LLM",
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
            # 8. Soru: LLM ile kişiselleştirilmiş takip sorusu üret
            # 7. soruya + tüm önceki cevaplara bakarak
            print(f"   [TAKİP] LLM ile kişiselleştirilmiş takip sorusu üretiliyor...", flush=True)
            
            # 7. sorunun metnini al
            last_scenario_text = ""
            if hasattr(self, 'last_scenario_question') and self.last_scenario_question:
                last_scenario_text = self.last_scenario_question.get('soru', '')
            
            # Takip sorusunu üret
            follow_up = self.generate_followup_question(last_scenario_text)
            
            return {
                "id": "SCENARIO_FOLLOW",
                "kategori": "senaryo",
                "soru": follow_up,
                "difficulty_level": 3,
                "etiketler": ["senaryo", "takip"],
                "prereq_tags": [],
                "follow_up_to": getattr(self, 'last_scenario_question', {}).get('id', 'SCENARIO'),
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

   
    def record_turn(self, question: Dict, answer: str, analysis: Dict, audio_score: Dict = None):
        """
        Mülakat turunu kaydet
        
        Args:
            question: Soru bilgisi
            answer: Kullanıcı cevabı
            analysis: LLM analizi (score, feedback, vb.)
            audio_score: Ses analizi skoru (overall_score, scores, confidence_level)
        """
        history_entry = {
            "id": question["id"],
            "kategori": question.get("kategori"),
            "soru": question.get("soru"),
            "answer": answer,
            "analysis": analysis,
            "difficulty": question.get("difficulty_level"),
            "tags": question.get("etiketler", [])  # Etiketleri kaydet (bağlamlı soru seçimi için)
        }
        
        # Ses skorunu ekle (varsa)
        if audio_score:
            history_entry["audio_score"] = audio_score
        
        self.history.append(history_entry)
        
        # Fazı ilerlet
        self.advance_phase()

    def generate_personal_scenario(self) -> Dict:
        """
        Tarihçedeki cevaplardan kısa bir özet çıkarıp Gemini'den
        kişiselleştirilmiş bir senaryo (ve takip sorusu) üretmesini ister.
        Döndürülen yapı: {"scenario": str, "follow_up": str}
        """
       
        last_answers = [h["answer"] for h in self.history[-6:]]
        summary = "\n".join(f"- {a[:200]}" for a in last_answers)  # İlk 200 karakter
        
        prompt = f"""Adayın önceki cevaplarına göre kişiselleştirilmiş bir senaryo sorusu oluştur.

Aday Cevapları:
{summary}

Görev:
1. Adayın deneyimine uygun gerçekçi bir iş senaryosu yaz (2-3 cümle)
2. Bu senaryoya derinlemesine bir takip sorusu ekle

Sadece JSON döndür:
{{"scenario": "senaryo sorusu buraya", "follow_up": "takip sorusu buraya"}}

Örnek:
{{"scenario": "Projenizde kritik bir bug bulundu ve müşteri toplantısı 2 saat sonra. Ekip lideri tatilde. Ne yaparsınız?", "follow_up": "Ekip bu çözümü kabul etmezse nasıl ilerlersiniz?"}}
"""
        
        model = genai.GenerativeModel("gemini-2.0-flash-exp")  # Daha hızlı model
        
        # Güvenlik ayarlarını gevşet
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        resp = model.generate_content(
            prompt, 
            generation_config=genai.types.GenerationConfig(max_output_tokens=250),
            safety_settings=safety_settings
        )
        
        try:
            text = resp.text
        except ValueError as e:
            print(f"Scenario response hatası: {e}")
            return {"scenario": "Kişiselleştirilmiş senaryo sorusu", "follow_up": "Bu durumda nasıl ilerlerdin?"}
        
        try:
            import json as _json
            import re
            
            # Markdown kod bloklarını temizle
            text_clean = re.sub(r'```json\s*', '', text)
            text_clean = re.sub(r'```\s*', '', text_clean)
            text_clean = text_clean.strip()
            
            # Önce direkt JSON parse dene
            try:
                parsed = _json.loads(text_clean)
                if isinstance(parsed, dict) and "scenario" in parsed and "follow_up" in parsed:
                    print(f"[OK] Senaryo başarıyla üretildi")
                    return parsed
            except:
                pass
            
            # JSON regex ile bul
            json_pattern = r'\{[^{}]*"scenario"[^{}]*"follow_up"[^{}]*\}'
            m = re.search(json_pattern, text, re.DOTALL)
            if m:
                try:
                    parsed = _json.loads(m.group(0))
                    print(f"[OK] Senaryo regex ile bulundu")
                    return parsed
                except:
                    pass
            
            # Son çare: satır satır parse
            print("[UYARI] JSON parse başarısız, fallback kullanılıyor")
            return {
                "scenario": "Ekibinizle bir projede çalışıyorsunuz. Kritik bir karar almanız gerekiyor ama ekip üyeleri farklı görüşlerde. Nasıl ilerlersiniz?",
                "follow_up": "Aldığınız kararı ekip kabul etmezse ne yaparsınız?"
            }
        except Exception as e:
            print(f"[HATA] Senaryo üretimi başarısız: {e}")
            return {
                "scenario": "Ekibinizle bir projede çalışıyorsunuz. Kritik bir karar almanız gerekiyor ama ekip üyeleri farklı görüşlerde. Nasıl ilerlersiniz?",
                "follow_up": "Aldığınız kararı ekip kabul etmezse ne yaparsınız?"
            }

    def generate_followup_question(self, scenario_text: str) -> str:
        """
        7. soruya (senaryo) ve tüm önceki cevaplara bakarak
        LLM ile kişiselleştirilmiş bir takip sorusu üretir.
        
        Args:
            scenario_text: 7. sorunun metni (senaryo sorusu)
            
        Returns:
            str: Takip sorusu metni
        """
        # Tüm cevapları özetle
        all_answers = [h["answer"] for h in self.history]
        summary = "\n".join(f"{i+1}. {a[:150]}" for i, a in enumerate(all_answers))
        
        prompt = f"""Aşağıdaki senaryo sorusuna ve adayın önceki cevaplarına bakarak, derinlemesine bir takip sorusu oluştur.

SENARYO SORUSU (7. Soru):
{scenario_text}

ADAYIN ÖNCEKİ CEVAPLARI (1-7. Sorular):
{summary}

GÖREV:
1. Senaryo sorusuna bağlı kalarak bir takip sorusu yaz
2. Adayın önceki cevaplarındaki deneyim/yaklaşımını dikkate al
3. Soruyu daha zorlaştıran veya farklı bir açıdan düşündüren bir durum ekle
4. Sadece soruyu döndür, açıklama ekleme

ÖRNEK TAKIP SORULARI:
- "Ekip bu çözümü kabul etmezse nasıl ilerlersiniz?"
- "Müşteri bu durumdan memnun kalmazsa ne yaparsınız?"
- "Bu kararın uzun vadeli sonuçları ne olabilir?"
- "Benzer bir durumla tekrar karşılaşmamak için hangi süreçleri önerirsiniz?"

Sadece takip sorusunu döndür (JSON değil, düz metin):
"""
        
        try:
            model = genai.GenerativeModel("gemini-2.0-flash-exp")
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            resp = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=150,
                    temperature=0.7
                ),
                safety_settings=safety_settings
            )
            
            follow_up = resp.text.strip()
            
            # Gereksiz karakterleri temizle
            follow_up = follow_up.replace('"', '').replace("'", "").strip()
            
            print(f"[OK] Takip sorusu üretildi: {follow_up[:80]}...", flush=True)
            return follow_up
            
        except Exception as e:
            print(f"[HATA] Takip sorusu üretimi başarısız: {e}", flush=True)
            # Fallback: Genel takip sorusu
            return "Aldığınız kararı ekip kabul etmezse veya beklenmedik bir sorun çıkarsa nasıl ilerlersiniz?"


