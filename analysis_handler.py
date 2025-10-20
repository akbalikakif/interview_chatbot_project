import os
import numpy as np
import librosa
from pydub import AudioSegment
from pydub.silence import detect_silence
import re

# Türkçe dolgu kelimeleri ve desenleri
FILLER_WORDS_TR = {
    'ee': ['ee', 'eee', 'eeee'],
    'mmm': ['mmm', 'mm', 'mmmm', 'hmmm'],
    'işte': ['işte', 'yani işte'],
    'yani': ['yani', 'yani işte'],
    'hani': ['hani', 'hanii'],
    'şey': ['şey', 'şeey'],
    'falan': ['falan', 'filan'],
    'felan': ['felan', 'filan'],
    'bilmem': ['bilmem', 'bilmemne'],
    'bir şey': ['bi şey', 'bir şey'],
    'nasıl desem': ['nasıl desem', 'nasıl diyeyim'],
    'tabii': ['tabii ki', 'tabi'],
    'herhalde': ['herhalde'],
    'öyle': ['öyle', 'böyle'],
    'gibi': ['gibi'],
    'mesela': ['mesela', 'meselâ'],
    'evet': ['evet evet', 'eveet'],
    'tamam': ['tamam tamam', 'tamamdır']
}

class AnalysisHandler:
    """Ses ve metin analizi için ana sınıf - Sadece analiz ve puanlama"""

    def __init__(self):
        print("Ses analizi sistemi hazır")
    def analyze_audio_file(self, audio_path: str) -> dict:
        print(f" Ses analizi başlıyor: {audio_path}")

        try:
            y, sr = librosa.load(audio_path, sr=16000)
            duration = librosa.get_duration(y=y, sr=sr)
            print(f"Ses süresi: {duration:.2f} saniye")

            # Sessizlik analizi
            long_pauses, short_pauses = self._analyze_silence(audio_path)

            # Konuşma hızı
            wpm, wpm_rating = self._estimate_wpm(y, sr, duration)

            # Ton analizi
            tone_rating, pitch_std = self._analyze_pitch(y, sr)

            # Enerji tutarlılığı
            consistency_score = self._analyze_energy(y)

            # Akıcılık skoru
            fluency_score = self._calculate_fluency_score(
                long_pauses, short_pauses, wpm, tone_rating, consistency_score
            )
            print(f"Akıcılık skoru: {fluency_score:.1f}/100")

            return {
                'fluency_score': round(fluency_score, 1),
                'wpm': round(wpm, 1),
                'wpm_rating': wpm_rating,
                'tone_rating': tone_rating,
                'pitch_std': round(pitch_std, 1),
                'long_pause_count': long_pauses,
                'short_pause_count': short_pauses,
                'energy_consistency': round(consistency_score, 2)
            }

        except Exception as e:
            print(f"Ses analizi hatası: {e}")
            return {'error': str(e)}

    def _analyze_silence(self, audio_path: str) -> tuple:
        """Sessizlikleri analiz eder - Sadece sayıları döndürür"""
        audio = AudioSegment.from_wav(audio_path)
        silences = detect_silence(audio, min_silence_len=500, silence_thresh=-40)

        pause_durations = [(end - start) / 1000.0 for start, end in silences]
        long_pauses = sum(1 for p in pause_durations if p > 2.0)
        short_pauses = sum(1 for p in pause_durations if p < 0.8)
        return long_pauses, short_pauses

    def _estimate_wpm(self, y, sr, duration) -> tuple:
        """Konuşma hızını tahmin eder - WPM ve rating döndürür"""
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units='time')
        estimated_words = len(onset_frames)
        wpm = (estimated_words / duration) * 60 if duration > 0 else 0

        if wpm < 100:
            rating = "yavaş"
        elif wpm > 180:
            rating = "hızlı"
        else:
            rating = "normal"

        return wpm, rating

    def _analyze_pitch(self, y, sr) -> tuple:
        """Ses tonu analizi - Rating ve std döndürür"""
        try:
            f0, _, _ = librosa.pyin(
                y,
                fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C7'),
                sr=sr
            )

            f0_clean = f0[~np.isnan(f0)]

            if len(f0_clean) == 0:
                return 'unknown', 0

            pitch_std = np.std(f0_clean)

            if pitch_std < 20:
                rating = "monoton"
            elif pitch_std > 50:
                rating = "çok değişken"
            else:
                rating = "dengeli"

            return rating, float(pitch_std)

        except Exception as e:
            print(f"Pitch analizi hatası: {e}")
            return 'unknown', 0

    def _analyze_energy(self, y) -> float:
        """Ses enerjisi tutarlılığı - Sadece consistency score döndürür"""
        rms = librosa.feature.rms(y=y)[0]
        avg_energy = np.mean(rms)
        energy_std = np.std(rms)

        consistency_score = 1.0 - min(energy_std / (avg_energy + 1e-6), 1.0)
        return consistency_score

    def _calculate_fluency_score(self, long_pauses, short_pauses, wpm, tone_rating, consistency) -> float:
        """Akıcılık skorunu hesaplar (0-100)"""
        score = 100.0

        # Duraksama cezaları
        score -= long_pauses * 5
        if short_pauses > 10:
            score -= ((short_pauses - 10) // 5) * 2

        # Konuşma hızı cezaları
        if wpm < 80 or wpm > 200:
            score -= 15
        elif wpm < 100 or wpm > 180:
            score -= 8

        # Enerji tutarlılığı bonusu
        score += consistency * 10

        # Ses tonu cezaları
        if tone_rating == 'monoton':
            score -= 10
        elif tone_rating == 'çok değişken':
            score -= 8

        return max(0, min(100, score))

    def analyze_text_for_fillers(self, text: str) -> dict:
        #"Dolgu kelime analizi"
        print(f"Metin analizi başlıyor")

        text_lower = text.lower()
        total_fillers = 0

        for category, variations in FILLER_WORDS_TR.items():
            for variation in variations:
                pattern = r'\b' + re.escape(variation) + r'\b'
                total_fillers += len(re.findall(pattern, text_lower))

        word_count = len(text.split())
        filler_ratio = (total_fillers / word_count * 100) if word_count > 0 else 0
        filler_score = max(0, 100 - (filler_ratio * 5))

        if filler_ratio < 3:
            rating = "mükemmel"
        elif filler_ratio < 6:
            rating = "iyi"
        elif filler_ratio < 10:
            rating = "orta"
        else:
            rating = "zayıf"

        print(f"Dolgu oranı: %{filler_ratio:.1f}, Skor: {filler_score:.1f}/100")

        return {
            'filler_score': round(filler_score, 1),
            'filler_ratio': round(filler_ratio, 1),
            'total_count': total_fillers,
            'rating': rating
        }

    def calculate_overall_score(self, audio_metrics: dict, text_metrics: dict = None) -> dict:
        # Genel performans skoru

        print("\n Genel skor hesaplanıyor...")

        # Akıcılık (ağırlık: 40%)
        fluency = audio_metrics.get('fluency_score', 0)

        # Dolgu kelimeleri (ağırlık: 30%)
        filler = text_metrics.get('filler_score', 0) if text_metrics else 0
        filler_weight = 0.30 if text_metrics else 0

        # Konuşma hızı (ağırlık: 15%)
        wpm = audio_metrics.get('wpm', 0)
        if 120 <= wpm <= 160:
            speed_score = 100
        elif 100 <= wpm <= 180:
            speed_score = 80
        else:
            speed_score = 60

        # Ses tonu (ağırlık: 15%)
        tone = audio_metrics.get('tone_rating', 'unknown')
        if tone == 'dengeli':
            tone_score = 100
        elif tone in ['monoton', 'çok değişken']:
            tone_score = 70
        else:
            tone_score = 50

        # Ağırlıklı ortalama
        if text_metrics:
            overall = (fluency * 0.40) + (filler * 0.30) + (speed_score * 0.15) + (tone_score * 0.15)
        else:
            overall = (fluency * 0.55) + (speed_score * 0.25) + (tone_score * 0.20)

        # Güvenilirlik seviyesi
        if overall >= 85:
            confidence = "yüksek"
        elif overall >= 70:
            confidence = "orta-yüksek"
        elif overall >= 60:
            confidence = "orta"
        else:
            confidence = "düşük"

        print(f"Genel skor: {overall:.1f}/100 ({confidence})")

        return {
            'overall_score': round(overall, 1),
            'confidence_level': confidence,
            'scores': {
                'akıcılık': round(fluency, 1),
                'dolgu_kelimeleri': round(filler, 1) if text_metrics else None,
                'konuşma_hızı': round(speed_score, 1),
                'ses_tonu': round(tone_score, 1)
            }
        }
