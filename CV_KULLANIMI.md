# 📄 CV Bazlı Kişiselleştirilmiş Mülakat

## 🎯 Özellik

CV Manager modülü, adayın CV'sini analiz ederek **teknik soruları kişiselleştirir**. 

### Nasıl Çalışır?

```
1. CV YÜKLEME (PDF/DOCX/TXT)
   ↓
2. METİN ÇIKARMA
   ↓
3. GEMINI İLE ANALİZ
   - Teknolojiler (Python, React, Docker, vb.)
   - Beceriler (API geliştirme, veritabanı tasarımı)
   - Deneyim alanları (backend, frontend, devops)
   ↓
4. ETİKET EŞLEŞTİRME
   - CV'deki "Python" → Soru havuzunda "python" etiketi
   - CV'deki "React" → Soru havuzunda "react" etiketi
   ↓
5. KİŞİSELLEŞTİRİLMİŞ MÜLAKAT
   - Teknik sorular adayın CV'sine göre
```

---

## 🚀 Kullanım

### 1. CV Olmadan Mülakat (Varsayılan)

```powershell
python main.py
```

**Sonuç:** Tüm sorular rastgele seçilir.

---

### 2. CV ile Mülakat (Kişiselleştirilmiş)

```powershell
# PDF ile
python main.py cv.pdf

# DOCX ile
python main.py my_resume.docx

# TXT ile
python main.py cv.txt
```

**Sonuç:** 
- Teknik sorular CV'deki teknolojilere göre seçilir
- Örnek: CV'de "Python" varsa → Python soruları sorulur
- Örnek: CV'de "React" varsa → React soruları sorulur

---

## 📊 CV Analizi Örneği

### Örnek CV:
```
Ahmet Yılmaz
Yazılım Geliştirici

Deneyim:
- 3 yıl Python backend geliştirme
- Django ve Flask ile REST API geliştirme
- Docker ve Kubernetes ile deployment
- PostgreSQL ve MongoDB veritabanı yönetimi
```

### Gemini Analizi:
```json
{
  "technologies": ["Python", "Django", "Flask", "Docker", "Kubernetes", "PostgreSQL", "MongoDB"],
  "skills": ["REST API geliştirme", "Backend geliştirme", "Veritabanı yönetimi"],
  "experience_areas": ["backend", "devops"],
  "years_of_experience": 3
}
```

### Eşleşen Etiketler:
```
['python', 'backend', 'oop', 'django', 'flask', 'docker', 'devops', 
 'container', 'kubernetes', 'sql', 'database', 'mongodb', 'nosql']
```

### Sorulacak Teknik Sorular:
- ✅ Python OOP soruları
- ✅ Backend mimarisi soruları
- ✅ Docker/Kubernetes soruları
- ✅ Veritabanı soruları
- ❌ Frontend soruları (CV'de yok)
- ❌ Mobile soruları (CV'de yok)

---

## 🔧 CV Manager API

### Programatik Kullanım

```python
from cv_manager import CVManager

# CV Manager oluştur
cv_manager = CVManager()

# CV yükle
if cv_manager.load_cv("cv.pdf"):
    # Analiz et
    analysis = cv_manager.analyze_cv_with_llm()
    
    # Etiketleri al
    tags = cv_manager.get_matching_tags()
    
    # Özet al
    summary = cv_manager.get_cv_summary()
    
    # Kaydet
    cv_manager.save_analysis("cv_analysis.json")
```

---

## 📁 Desteklenen Formatlar

| Format | Kütüphane | Durum |
|--------|-----------|-------|
| **PDF** | pdfplumber | ✅ Destekleniyor |
| **DOCX** | python-docx | ✅ Destekleniyor |
| **TXT** | Built-in | ✅ Destekleniyor |

---

## 🧪 Test

### CV Manager Testi

```powershell
python cv_manager.py
```

**Beklenen Çıktı:**
```
=== CV MANAGER TEST ===

✅ CV başarıyla yüklendi (450 karakter)

🔍 CV analiz ediliyor (Gemini)...
✅ CV analizi tamamlandı
   Teknolojiler: Python, Django, Flask, Docker, Kubernetes
   Deneyim: 3 yıl
   Alanlar: backend, devops

=== ANALİZ SONUÇLARI ===
Teknolojiler: ['Python', 'Django', 'Flask', 'Docker', 'Kubernetes']
Beceriler: ['REST API geliştirme', 'Backend geliştirme']
Deneyim Alanları: ['backend', 'devops']
Deneyim Yılı: 3

=== EŞLEŞTİRME ETİKETLERİ ===
Etiketler: ['python', 'backend', 'oop', 'django', 'flask', ...]
```

---

## 🎯 Soru Eşleştirme Mantığı

### Teknoloji → Etiket Eşleştirmesi

| CV'deki Teknoloji | Eşleşen Etiketler |
|-------------------|-------------------|
| Python | `python`, `backend`, `oop` |
| JavaScript | `javascript`, `frontend` |
| React | `react`, `frontend`, `javascript` |
| Docker | `docker`, `devops`, `container` |
| Kubernetes | `kubernetes`, `devops`, `container` |
| AWS | `aws`, `cloud`, `devops` |
| SQL | `sql`, `database`, `backend` |
| MongoDB | `mongodb`, `nosql`, `database` |

### Soru Havuzunda Etiketler

Soru JSON dosyalarında `tags` alanı:

```json
{
  "id": "Q001",
  "kategori": "teknik",
  "soru": "Python'da OOP nedir?",
  "tags": ["python", "oop", "backend"],
  "anahtar_kelimeler": ["sınıf", "nesne", "inheritance"]
}
```

**Eşleştirme:** CV'deki `python` etiketi → Soru'daki `python` etiketi ✅

---

## ⚙️ Ayarlar

### Gemini API Anahtarı

`.env` dosyasında:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

### Güvenlik Ayarları

CV analizi için güvenlik filtreleri gevşetilmiştir (`cv_manager.py` satır 513-518):

```python
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]
```

---

## 🔍 Sorun Giderme

### "pdfplumber yüklü değil" Hatası

```powershell
pip install pdfplumber
```

### "python-docx yüklü değil" Hatası

```powershell
pip install python-docx
```

### CV Analizi Başarısız

**Sorun:** Gemini API güvenlik filtresi

**Çözüm:** CV'nizde hassas bilgiler varsa, bunları kaldırın veya TXT formatında basitleştirilmiş bir CV kullanın.

---

## 📈 Avantajlar

### CV Olmadan:
- ❌ Rastgele teknik sorular
- ❌ Adayın bilmediği teknolojiler sorulabilir
- ❌ Genel mülakat

### CV ile:
- ✅ Kişiselleştirilmiş teknik sorular
- ✅ Adayın bildiği teknolojiler sorulur
- ✅ Daha adil değerlendirme
- ✅ Daha yüksek kaliteli mülakat

---

## 🎉 Sonuç

CV Manager ile:
1. ✅ CV otomatik analiz edilir
2. ✅ Teknolojiler ve beceriler çıkarılır
3. ✅ Soru havuzundan eşleşen sorular seçilir
4. ✅ Kişiselleştirilmiş mülakat yapılır

**Kullanım:**
```powershell
python main.py my_cv.pdf
```

**İyi şanslar! 🚀**
