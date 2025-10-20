"""
cv_manager.py
CV yükleme, metin çıkarma ve anahtar kelime analizi modülü
"""

import os
import re
from typing import Dict, List, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# PDF ve DOCX okuma için kütüphaneler
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    print("⚠️ pdfplumber yüklü değil. PDF okuma için: pip install pdfplumber")
    PDF_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    print("⚠️ python-docx yüklü değil. DOCX okuma için: pip install python-docx")
    DOCX_AVAILABLE = False

load_dotenv()

class CVManager:
    """CV yükleme ve analiz sınıfı"""
    
    def __init__(self):
        self.cv_text = ""
        self.cv_analysis = {}
        self.keywords = []
        self.technologies = []
        
        # Gemini API ayarla
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY bulunamadı. .env dosyasını kontrol edin.")
        genai.configure(api_key=api_key)
    
    def load_cv(self, file_path: str) -> bool:
        """CV dosyasını yükle ve metni çıkar"""
        if not os.path.exists(file_path):
            print(f"❌ Dosya bulunamadı: {file_path}")
            return False
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == '.pdf':
                self.cv_text = self._extract_from_pdf(file_path)
            elif file_ext in ['.docx', '.doc']:
                self.cv_text = self._extract_from_docx(file_path)
            elif file_ext == '.txt':
                self.cv_text = self._extract_from_txt(file_path)
            else:
                print(f"❌ Desteklenmeyen dosya formatı: {file_ext}")
                return False
            
            if self.cv_text:
                print(f"✅ CV başarıyla yüklendi ({len(self.cv_text)} karakter)")
                return True
            else:
                print("❌ CV metni çıkarılamadı")
                return False
                
        except Exception as e:
            print(f"❌ CV yükleme hatası: {e}")
            return False
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """PDF'den metin çıkar"""
        if not PDF_AVAILABLE:
            raise ImportError("pdfplumber yüklü değil")
        
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    
    def _extract_from_docx(self, file_path: str) -> str:
        """DOCX'ten metin çıkar"""
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx yüklü değil")
        
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    
    def _extract_from_txt(self, file_path: str) -> str:
        """TXT dosyasından metin oku"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
    def analyze_cv_with_llm(self) -> Dict:
        """CV'yi Gemini ile analiz et - anahtar kelimeler, teknolojiler, deneyim"""
        if not self.cv_text:
            print("❌ CV metni yok. Önce load_cv() çağırın.")
            return {}
        
        print("\n🔍 CV analiz ediliyor (Gemini)...")
        
        prompt = f"""
Aşağıdaki CV metnini analiz et ve şu bilgileri JSON formatında çıkar:

1. **technologies**: Kullanılan teknolojiler, programlama dilleri, framework'ler (liste)
2. **skills**: Teknik beceriler ve yetenekler (liste)
3. **experience_areas**: Deneyim alanları (backend, frontend, devops, vb.) (liste)
4. **key_projects**: Önemli projeler veya başarılar (kısa özet, liste)
5. **education**: Eğitim bilgisi (kısa özet, string)
6. **years_of_experience**: Tahmini deneyim yılı (sayı, eğer belirtilmemişse 0)

ÖNEMLI: Sadece JSON döndür, başka açıklama ekleme.

CV Metni:
{self.cv_text[:3000]}

JSON formatı:
{{
  "technologies": ["Python", "React", "Docker"],
  "skills": ["API geliştirme", "Veritabanı tasarımı"],
  "experience_areas": ["backend", "devops"],
  "key_projects": ["E-ticaret platformu geliştirme", "Mikroservis mimarisi"],
  "education": "Bilgisayar Mühendisliği, XYZ Üniversitesi",
  "years_of_experience": 3
}}
"""
        
        try:
            model = genai.GenerativeModel("gemini-2.0-flash-exp")
            
            # Güvenlik ayarları
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1000,
                    temperature=0.3
                ),
                safety_settings=safety_settings
            )
            
            # JSON parse
            import json
            text = response.text.strip()
            
            # JSON'u bul ve parse et
            try:
                # Direkt parse dene
                self.cv_analysis = json.loads(text)
            except:
                # JSON bloğunu bul
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    self.cv_analysis = json.loads(json_match.group(0))
                else:
                    raise ValueError("JSON bulunamadı")
            
            # Anahtar kelimeleri birleştir
            self.technologies = self.cv_analysis.get('technologies', [])
            self.keywords = (
                self.technologies + 
                self.cv_analysis.get('skills', []) + 
                self.cv_analysis.get('experience_areas', [])
            )
            
            print("✅ CV analizi tamamlandı")
            print(f"   Teknolojiler: {', '.join(self.technologies[:5])}")
            print(f"   Deneyim: {self.cv_analysis.get('years_of_experience', 0)} yıl")
            print(f"   Alanlar: {', '.join(self.cv_analysis.get('experience_areas', []))}")
            
            return self.cv_analysis
            
        except Exception as e:
            print(f"❌ CV analiz hatası: {e}")
            return {}
    
    def get_matching_tags(self) -> List[str]:
        """Soru havuzuyla eşleşecek etiketleri döndür"""
        if not self.keywords:
            return []
        
        # Teknolojileri küçük harfe çevir ve normalize et
        tags = []
        for tech in self.technologies:
            tech_lower = tech.lower()
            tags.append(tech_lower)
            
            # Yaygın eşleştirmeler
            if 'python' in tech_lower:
                tags.extend(['python', 'backend', 'oop'])
            elif 'java' in tech_lower and 'javascript' not in tech_lower:
                tags.extend(['java', 'backend', 'oop'])
            elif 'javascript' in tech_lower or 'js' in tech_lower:
                tags.extend(['javascript', 'frontend'])
            elif 'react' in tech_lower:
                tags.extend(['react', 'frontend', 'javascript'])
            elif 'angular' in tech_lower:
                tags.extend(['angular', 'frontend', 'javascript'])
            elif 'vue' in tech_lower:
                tags.extend(['vue', 'frontend', 'javascript'])
            elif 'node' in tech_lower:
                tags.extend(['nodejs', 'backend', 'javascript'])
            elif 'docker' in tech_lower:
                tags.extend(['docker', 'devops', 'container'])
            elif 'kubernetes' in tech_lower or 'k8s' in tech_lower:
                tags.extend(['kubernetes', 'devops', 'container'])
            elif 'aws' in tech_lower:
                tags.extend(['aws', 'cloud', 'devops'])
            elif 'azure' in tech_lower:
                tags.extend(['azure', 'cloud', 'devops'])
            elif 'sql' in tech_lower or 'database' in tech_lower:
                tags.extend(['sql', 'database', 'backend'])
            elif 'mongodb' in tech_lower or 'nosql' in tech_lower:
                tags.extend(['mongodb', 'nosql', 'database'])
            elif 'git' in tech_lower:
                tags.extend(['git', 'version-control'])
            elif 'ci/cd' in tech_lower or 'jenkins' in tech_lower:
                tags.extend(['ci-cd', 'devops'])
            elif 'test' in tech_lower:
                tags.extend(['testing', 'qa', 'unit-test'])
        
        # Deneyim alanlarını ekle
        for area in self.cv_analysis.get('experience_areas', []):
            tags.append(area.lower())
        
        # Tekrarları kaldır
        return list(set(tags))
    
    def get_cv_summary(self) -> str:
        """CV özeti döndür (raporlama için)"""
        if not self.cv_analysis:
            return "CV analizi yapılmadı"
        
        summary = f"""
CV Özeti:
- Teknolojiler: {', '.join(self.technologies[:10])}
- Deneyim: {self.cv_analysis.get('years_of_experience', 0)} yıl
- Alanlar: {', '.join(self.cv_analysis.get('experience_areas', []))}
- Eğitim: {self.cv_analysis.get('education', 'Belirtilmemiş')}
"""
        return summary.strip()
    
    def save_analysis(self, output_path: str = "cv_analysis.json"):
        """CV analizini JSON olarak kaydet"""
        if not self.cv_analysis:
            print("❌ Kaydedilecek analiz yok")
            return False
        
        try:
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.cv_analysis, f, ensure_ascii=False, indent=2)
            print(f"✅ CV analizi kaydedildi: {output_path}")
            return True
        except Exception as e:
            print(f"❌ Kaydetme hatası: {e}")
            return False


def test_cv_manager():
    """CV Manager test fonksiyonu"""
    print("=== CV MANAGER TEST ===\n")
    
    cv_manager = CVManager()
    
    # Test CV metni
    test_cv = """
    Ahmet Yılmaz
    Yazılım Geliştirici
    
    Deneyim:
    - 3 yıl Python backend geliştirme
    - Django ve Flask ile REST API geliştirme
    - Docker ve Kubernetes ile deployment
    - PostgreSQL ve MongoDB veritabanı yönetimi
    - AWS cloud servisleri kullanımı
    - Git ile versiyon kontrolü
    - Unit test ve integration test yazımı
    
    Projeler:
    - E-ticaret platformu (Django, React, PostgreSQL)
    - Mikroservis mimarisi (FastAPI, Docker, Kubernetes)
    
    Eğitim:
    Bilgisayar Mühendisliği, İTÜ
    """
    
    # Test CV'yi kaydet
    with open("test_cv.txt", "w", encoding="utf-8") as f:
        f.write(test_cv)
    
    # CV yükle
    if cv_manager.load_cv("test_cv.txt"):
        # Analiz et
        analysis = cv_manager.analyze_cv_with_llm()
        
        if analysis:
            print("\n=== ANALİZ SONUÇLARI ===")
            print(f"Teknolojiler: {analysis.get('technologies', [])}")
            print(f"Beceriler: {analysis.get('skills', [])}")
            print(f"Deneyim Alanları: {analysis.get('experience_areas', [])}")
            print(f"Deneyim Yılı: {analysis.get('years_of_experience', 0)}")
            
            print("\n=== EŞLEŞTİRME ETİKETLERİ ===")
            tags = cv_manager.get_matching_tags()
            print(f"Etiketler: {tags}")
            
            print("\n=== CV ÖZETİ ===")
            print(cv_manager.get_cv_summary())
    
    # Test dosyasını sil
    if os.path.exists("test_cv.txt"):
        os.remove("test_cv.txt")


if __name__ == "__main__":
    test_cv_manager()
