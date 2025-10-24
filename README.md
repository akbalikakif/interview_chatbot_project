# 🎤 Akıllı Mülakat Sistemi - Kullanıcı Kılavuzu

## 🎯 Yeni Özellikler (v2.0)

### ✨ Kullanıcı Profili ve Gelişim Takibi

Artık her kullanıcı için:
- 📝 **Kişisel profil** oluşturulur
- 📊 **Mülakat geçmişi** saklanır
- 📈 **Gelişim grafikleri** otomatik oluşturulur
- 🎯 **İstatistikler** takip edilir

---

## 🚀 Hızlı Başlangıç

### 1. İlk Kullanım

```bash
python main.py
```

**Sistem sırayla şunları soracak:**

#### a) Kullanıcı Girişi
```
👤 KULLANICI GİRİŞİ
==================

🔹 Mevcut kullanıcı olarak devam etmek için numara girin
🔹 Yeni kullanıcı için 'y' yazın
🔹 Sesli kayıt için 's' yazın

>>> 
```

**Seçenekler:**
- **Numara (1, 2, 3...)**: Mevcut kullanıcı olarak devam
- **'y'**: Yeni kullanıcı (manuel isim girişi)
- **'s'**: Sesli isim kaydı (mikrofona söyleyin)

#### b) Sesli İsim Kaydı (Önerilen)

```
🎤 KULLANICI KAYDI
==================

Lütfen adınızı ve soyadınızı söyleyin...
Örnek: 'Ahmet Yılmaz' veya 'Ayşe Demir'

🎤 Konuşmaya başlayın...
🔴 Kayıt başladı...
✅ Kayıt tamamlandı.

✅ Algılanan isim: 'Ahmet Yılmaz'

Bu isim doğru mu? (Evet için Enter, Hayır için 'h' yazın)
>>> 
```

#### c) CV Yükleme (Opsiyonel)

Sistem otomatik olarak ana dizinde şu isimlerdeki CV'leri arar:
- `cv.pdf`, `CV.docx`
- `resume.pdf`, `Resume.docx`
- `ozgecmis.pdf`, `ozgeçmiş.docx`

**Bulunamazsa:**
```
ℹ️  CV dosyası bulunamadı. Mülakat CV olmadan başlayacak.
   CV eklemek için: Ana dizine 'cv.pdf', 'resume.docx' veya 'ozgecmis.txt' koyun
```

---

## 📊 Mülakat Akışı

```
=== Akıllı Mülakat Sistemi ===
Mülakat akışı:
1. Kişisel soru (bağımsız)
2. Kişisel soru (bağımsız)
3. Teknik soru (bağımsız, CV bazlı)
4. Teknik soru (3. soruya bağlı)
5. Teknik soru (bağımsız)
6. Teknik soru (5. soruya bağlı)
7. Senaryo sorusu 
8. Takip sorusu (kişiselleştirilmiş)
```

### Her Soru İçin:

1. **Soru Okunur** (TTS ile sesli)
2. **Cevap Beklenir** (STT ile sesli kayıt)
   - İlk 3 saniye: Hazırlanma süresi
   - Konuşma: Gerçek zamanlı transkripsiyon
   - 3 saniye sessizlik: Otomatik bitiş
3. **Değerlendirme** (Gemini AI)
   - İçerik analizi
   - Ses analizi (akıcılık, hız, ton)
4. **Puan ve Geri Bildirim**

---

## 📈 Mülakat Sonrası

### 1. Anlık İstatistikler

```
📊 Mülakat İstatistikleri:
   Toplam Mülakat: 3
   Bu Mülakat Skoru: 7.5/10
   Ortalama Skor: 7.2/10
   En İyi Skor: 8.1/10
   Gelişim: 📈 12.5%
```

### 2. Gelişim Grafikleri

Otomatik olarak 4 grafik oluşturulur:

#### a) **Genel Gelişim Grafiği** (Çizgi Grafik)
- Genel skor
- İçerik skoru
- Ses skoru
- Trend çizgisi

#### b) **Faz Karşılaştırma** (Bar Chart)
- Son mülakat vs Ortalama
- Kişisel, Teknik, Senaryo fazları

#### c) **Yetenek Haritası** (Radar Chart)
- Kişisel Beceriler
- Teknik Bilgi
- Problem Çözme

#### d) **Kümülatif Gelişim** (Alan Grafiği)
- Fazların birikimlı gelişimi

**Grafikler kaydedilir:** `charts/<kullanıcı_adı>/`

### 3. Detaylı PDF Raporu

**İçerik:**
- ✅ Genel bilgiler (ad, tarih, soru sayısı)
- ✅ Genel performans tablosu
- ✅ Faz bazında performans
- ✅ **Gelişim grafikleri** (4 adet)
- ✅ Öneriler
- ✅ Detaylı soru analizi

**Kaydedilir:** `reports/interview_report_YYYYMMDD_HHMMSS.pdf`

### 4. Word Raporu

**Kaydedilir:** `reports/interview_report_YYYYMMDD_HHMMSS.docx`

---

## 📁 Dosya Yapısı

```
interview_chatbot_project/
├── main.py                    # Ana program
├── user_profile.py            # 🆕 Kullanıcı profil yönetimi
├── progress_charts.py         # 🆕 Gelişim grafikleri
├── reports.py                 # Gelişmiş rapor sistemi
├── llm_handler.py             # LLM entegrasyonu
├── speech_to_text.py          # Streaming STT
├── text_to_speech.py          # TTS
├── audio_analysis.py          # Ses analizi
├── cv_manager.py              # CV analizi
│
├── user_data/                 # 🆕 Kullanıcı profilleri
│   ├── Ahmet_Yilmaz.json
│   ├── Ayse_Demir.json
│   └── ...
│
├── charts/                    # 🆕 Gelişim grafikleri
│   ├── Ahmet_Yilmaz/
│   │   ├── overall_progress.png
│   │   ├── phase_comparison.png
│   │   ├── radar_chart.png
│   │   └── improvement_trend.png
│   └── ...
│
├── reports/                   # PDF/Word raporları
│   ├── interview_report_20250125_143022.pdf
│   └── interview_report_20250125_143022.docx
│
├── data/                      # Geçici ses dosyaları
│   ├── soru-1.wav
│   └── ...
│
└── question_pool/             # Soru havuzu
    ├── kisisel_sorular.json
    ├── teknik_sorular.json
    └── senaryo_sorular.json
```

---

## 🎯 Kullanım Senaryoları

### Senaryo 1: İlk Mülakat

```bash
python main.py
```

1. Sesli isim kaydı: "Ahmet Yılmaz"
2. CV yükleme: `cv.pdf` (otomatik bulunur)
3. 8 soru cevapla
4. Sonuç: İlk mülakat raporu + grafikler

### Senaryo 2: İkinci Mülakat (Gelişim Takibi)

```bash
python main.py
```

1. Mevcut kullanıcı seç: `1` (Ahmet Yılmaz)
2. Sistem önceki mülakatı gösterir:
   ```
   📂 Profil yüklendi: Ahmet Yılmaz
      Toplam mülakat sayısı: 1
      Son mülakat: 2025-01-25 14:30 - Skor: 7.5/10
   ```
3. 8 soru cevapla
4. Sonuç: 
   - Karşılaştırmalı grafikler (1. vs 2. mülakat)
   - Gelişim yüzdesi
   - Trend analizi

### Senaryo 3: Çoklu Kullanıcı

```bash
# Kullanıcı 1
python main.py
>>> s  # Sesli kayıt
>>> "Ahmet Yılmaz"

# Kullanıcı 2
python main.py
>>> s  # Sesli kayıt
>>> "Ayşe Demir"

# Kullanıcı 1 tekrar
python main.py
>>> 1  # Ahmet Yılmaz seç
```

---

## 📊 Gelişim Takibi Nasıl Çalışır?

### 1. Profil Oluşturma

İlk mülakatınızda:
```json
{
  "username": "Ahmet Yılmaz",
  "created_at": "2025-01-25 14:30:00",
  "interviews": []
}
```

### 2. Mülakat Kaydı

Her mülakat sonrası:
```json
{
  "interviews": [
    {
      "date": "2025-01-25 14:30:00",
      "overall_score": 7.5,
      "content_score": 7.8,
      "audio_score": 7.0,
      "phase_scores": {
        "kişisel": 8.0,
        "teknik": 7.2,
        "senaryo": 7.3
      },
      "question_count": 8,
      "answers": [...]
    }
  ]
}
```

### 3. İstatistik Hesaplama

- **Ortalama Skor**: Tüm mülakatların ortalaması
- **En İyi/En Kötü**: Min/Max skorlar
- **Gelişim Oranı**: Son 3 vs önceki 3 mülakat karşılaştırması

### 4. Grafik Oluşturma

Her mülakat sonrası otomatik:
- Çizgi grafikler (trend)
- Bar grafikler (karşılaştırma)
- Radar grafikler (yetenek haritası)
- Alan grafikler (kümülatif)

---

## 🎨 Grafik Örnekleri

### Genel Gelişim
```
Skor
10 ┤                           ●
 9 ┤                     ●
 8 ┤               ●
 7 ┤         ●
 6 ┤   ●
 5 ┤
   └─────────────────────────────
     M1  M2  M3  M4  M5  M6
     
     ● Genel Skor
     ■ İçerik Skoru
     ▲ Ses Skoru
```

### Faz Karşılaştırma
```
Skor
10 ┤
 8 ┤  ██    ██    ██
 6 ┤  ██    ██    ██
 4 ┤  ██    ██    ██
 2 ┤  ██    ██    ██
   └──────────────────
     Kişisel Teknik Senaryo
     
     ██ Son Mülakat
     ▓▓ Ortalama
```

---

## 💡 İpuçları

### Sesli İsim Kaydı
- ✅ Net ve yavaş konuşun
- ✅ Sadece ad-soyad söyleyin
- ✅ Sessiz ortamda kayıt yapın
- ❌ Uzun cümleler kurmayın

### Mülakat Cevapları
- ✅ İlk 3 saniye: Düşünme süresi
- ✅ Net ve akıcı konuşun
- ✅ Teknik terimleri doğru telaffuz edin
- ✅ 3 saniye sessizlik: Otomatik bitiş

### Gelişim Takibi
- 📊 En az 2 mülakat: Trend analizi
- 📊 En az 6 mülakat: Gelişim oranı hesabı
- 📊 Düzenli mülakat: Daha iyi grafikler

---

## 🔧 Sorun Giderme

### "CV bulunamadı"
**Çözüm:** Ana dizine `cv.pdf` veya `resume.docx` koyun

### "Ses algılanamadı"
**Çözüm:** 
- Mikrofon izinlerini kontrol edin
- Sessiz ortamda tekrar deneyin
- Manuel metin girişi yapın

### "Grafik oluşturulamadı"
**Çözüm:** 
```bash
pip install matplotlib
```

### "Profil yüklenemedi"
**Çözüm:** 
- `user_data/` klasörünü kontrol edin
- Yeni profil oluşturun

---

## 📞 Destek

Sorun yaşarsanız:
1. `user_data/` klasöründeki JSON dosyasını kontrol edin
2. `charts/` klasöründeki grafikleri kontrol edin
3. `reports/` klasöründeki PDF'i açın

---

## 🎉 Özet

**Yeni Sistem:**
- ✅ Sesli isim kaydı
- ✅ Kullanıcı profilleri
- ✅ Mülakat geçmişi
- ✅ 4 farklı gelişim grafiği
- ✅ Karşılaştırmalı analiz
- ✅ Trend takibi
- ✅ PDF'de grafikler

**Kullanım:**
1. `python main.py`
2. İsim söyle/yaz
3. Mülakata gir
4. Grafiklerini gör
5. Gelişimini takip et

**Başarılar!** 🚀
