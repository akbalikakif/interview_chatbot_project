"""
progress_charts.py
Kullanıcı gelişim grafiklerini oluşturur
"""

import os
import matplotlib
matplotlib.use('Agg')  # GUI olmadan çalışması için
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib import rcParams
import numpy as np
from typing import List, Dict
from datetime import datetime

# Türkçe karakter desteği
try:
    # Windows için Arial font
    font_path = "C:/Windows/Fonts/Arial.ttf"
    if os.path.exists(font_path):
        prop = fm.FontProperties(fname=font_path)
        rcParams['font.family'] = prop.get_name()
    rcParams['axes.unicode_minus'] = False
except Exception as e:
    print(f"⚠️ Font ayarı hatası: {e}")

# Grafik klasörü
CHARTS_DIR = "charts"
if not os.path.exists(CHARTS_DIR):
    os.makedirs(CHARTS_DIR)

class ProgressCharts:
    """Kullanıcı gelişim grafiklerini oluşturur"""
    
    def __init__(self, username: str):
        self.username = username
        self.charts_dir = os.path.join(CHARTS_DIR, self._safe_filename(username))
        
        if not os.path.exists(self.charts_dir):
            os.makedirs(self.charts_dir)
    
    def _safe_filename(self, name: str) -> str:
        """Dosya adı için güvenli string"""
        return "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    
    def create_overall_progress_chart(self, interviews: List[Dict]) -> str:
        """Genel gelişim grafiği (çizgi grafik)"""
        if not interviews:
            return None
        
        # Veri hazırlama
        dates = []
        overall_scores = []
        content_scores = []
        audio_scores = []
        
        for i, interview in enumerate(interviews, 1):
            dates.append(f"Mülakat {i}")
            overall_scores.append(interview.get('overall_score', 0))
            content_scores.append(interview.get('content_score', 0))
            audio_scores.append(interview.get('audio_score', 0))
        
        # Grafik oluştur
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = np.arange(len(dates))
        
        ax.plot(x, overall_scores, marker='o', linewidth=2, markersize=8, 
                label='Genel Skor', color='#2E86AB', linestyle='-')
        ax.plot(x, content_scores, marker='s', linewidth=2, markersize=6, 
                label='İçerik Skoru', color='#A23B72', linestyle='--')
        ax.plot(x, audio_scores, marker='^', linewidth=2, markersize=6, 
                label='Ses Skoru', color='#F18F01', linestyle=':')
        
        ax.set_xlabel('Mülakat', fontsize=12, fontweight='bold')
        ax.set_ylabel('Skor (0-10)', fontsize=12, fontweight='bold')
        ax.set_title(f'{self.username} - Genel Gelişim Grafiği', 
                     fontsize=14, fontweight='bold', pad=20)
        
        ax.set_xticks(x)
        ax.set_xticklabels(dates, rotation=45, ha='right')
        ax.set_ylim(0, 10)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='best', fontsize=10)
        
        # Trend çizgisi ekle
        if len(overall_scores) >= 2:
            z = np.polyfit(x, overall_scores, 1)
            p = np.poly1d(z)
            ax.plot(x, p(x), "r--", alpha=0.3, linewidth=1, label='Trend')
        
        plt.tight_layout()
        
        filepath = os.path.join(self.charts_dir, 'overall_progress.png')
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📊 Genel gelişim grafiği oluşturuldu: {filepath}")
        return filepath
    
    def create_phase_comparison_chart(self, interviews: List[Dict]) -> str:
        """Faz bazında karşılaştırma (bar chart)"""
        if not interviews:
            return None
        
        # Son mülakatın faz skorları
        latest_interview = interviews[-1]
        phase_scores = latest_interview.get('phase_scores', {})
        
        if not phase_scores:
            return None
        
        # Tüm mülakatların ortalaması
        all_phase_scores = {'kişisel': [], 'teknik': [], 'senaryo': []}
        
        for interview in interviews:
            for phase, score in interview.get('phase_scores', {}).items():
                if phase in all_phase_scores:
                    all_phase_scores[phase].append(score)
        
        # Ortalama hesapla
        avg_scores = {}
        for phase, scores in all_phase_scores.items():
            avg_scores[phase] = sum(scores) / len(scores) if scores else 0
        
        # Grafik oluştur
        fig, ax = plt.subplots(figsize=(10, 6))
        
        phases = list(phase_scores.keys())
        latest_values = [phase_scores.get(p, 0) for p in phases]
        avg_values = [avg_scores.get(p, 0) for p in phases]
        
        x = np.arange(len(phases))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, latest_values, width, label='Son Mülakat', 
                       color='#2E86AB', alpha=0.8)
        bars2 = ax.bar(x + width/2, avg_values, width, label='Ortalama', 
                       color='#F18F01', alpha=0.8)
        
        ax.set_xlabel('Faz', fontsize=12, fontweight='bold')
        ax.set_ylabel('Skor (0-10)', fontsize=12, fontweight='bold')
        ax.set_title(f'{self.username} - Faz Bazında Performans', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels([p.capitalize() for p in phases])
        ax.set_ylim(0, 10)
        ax.legend(fontsize=10)
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')
        
        # Değerleri barların üstüne yaz
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}',
                       ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        filepath = os.path.join(self.charts_dir, 'phase_comparison.png')
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📊 Faz karşılaştırma grafiği oluşturuldu: {filepath}")
        return filepath
    
    def create_radar_chart(self, interviews: List[Dict]) -> str:
        """Radar chart (yetenek haritası)"""
        if not interviews:
            return None
        
        latest_interview = interviews[-1]
        phase_scores = latest_interview.get('phase_scores', {})
        
        if not phase_scores:
            return None
        
        # Kategoriler
        categories = ['Kişisel\nBeceriler', 'Teknik\nBilgi', 'Problem\nÇözme']
        values = [
            phase_scores.get('kişisel', 0),
            phase_scores.get('teknik', 0),
            phase_scores.get('senaryo', 0)
        ]
        
        # Radar chart için açılar
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        values += values[:1]  # Döngüyü kapat
        angles += angles[:1]
        
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
        
        ax.plot(angles, values, 'o-', linewidth=2, color='#2E86AB', label='Mevcut')
        ax.fill(angles, values, alpha=0.25, color='#2E86AB')
        
        # Ortalama ekle (varsa)
        if len(interviews) >= 2:
            all_phase_scores = {'kişisel': [], 'teknik': [], 'senaryo': []}
            for interview in interviews[:-1]:  # Son hariç
                for phase, score in interview.get('phase_scores', {}).items():
                    if phase in all_phase_scores:
                        all_phase_scores[phase].append(score)
            
            avg_values = [
                sum(all_phase_scores['kişisel']) / len(all_phase_scores['kişisel']) if all_phase_scores['kişisel'] else 0,
                sum(all_phase_scores['teknik']) / len(all_phase_scores['teknik']) if all_phase_scores['teknik'] else 0,
                sum(all_phase_scores['senaryo']) / len(all_phase_scores['senaryo']) if all_phase_scores['senaryo'] else 0
            ]
            avg_values += avg_values[:1]
            
            ax.plot(angles, avg_values, 'o--', linewidth=2, color='#F18F01', 
                   alpha=0.7, label='Önceki Ortalama')
            ax.fill(angles, avg_values, alpha=0.15, color='#F18F01')
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=11)
        ax.set_ylim(0, 10)
        ax.set_yticks([2, 4, 6, 8, 10])
        ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=9)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.set_title(f'{self.username} - Yetenek Haritası', 
                     fontsize=14, fontweight='bold', pad=30)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10)
        
        plt.tight_layout()
        
        filepath = os.path.join(self.charts_dir, 'radar_chart.png')
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📊 Radar grafiği oluşturuldu: {filepath}")
        return filepath
    
    def create_improvement_trend_chart(self, interviews: List[Dict]) -> str:
        """İyileşme trendi (alan grafiği)"""
        if len(interviews) < 2:
            return None
        
        dates = [f"M{i}" for i in range(1, len(interviews) + 1)]
        
        # Faz skorlarını topla
        personal_scores = []
        technical_scores = []
        scenario_scores = []
        
        for interview in interviews:
            phase_scores = interview.get('phase_scores', {})
            personal_scores.append(phase_scores.get('kişisel', 0))
            technical_scores.append(phase_scores.get('teknik', 0))
            scenario_scores.append(phase_scores.get('senaryo', 0))
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = np.arange(len(dates))
        
        ax.fill_between(x, 0, personal_scores, alpha=0.3, color='#2E86AB', label='Kişisel')
        ax.fill_between(x, personal_scores, 
                        [p+t for p, t in zip(personal_scores, technical_scores)], 
                        alpha=0.3, color='#A23B72', label='Teknik')
        ax.fill_between(x, [p+t for p, t in zip(personal_scores, technical_scores)],
                        [p+t+s for p, t, s in zip(personal_scores, technical_scores, scenario_scores)],
                        alpha=0.3, color='#F18F01', label='Senaryo')
        
        ax.set_xlabel('Mülakat', fontsize=12, fontweight='bold')
        ax.set_ylabel('Toplam Skor', fontsize=12, fontweight='bold')
        ax.set_title(f'{self.username} - Kümülatif Gelişim', 
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(dates)
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        
        filepath = os.path.join(self.charts_dir, 'improvement_trend.png')
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📊 İyileşme trendi grafiği oluşturuldu: {filepath}")
        return filepath
    
    def generate_all_charts(self, interviews: List[Dict]) -> Dict[str, str]:
        """Tüm grafikleri oluşturur"""
        print(f"\n📊 {self.username} için grafikler oluşturuluyor...")
        
        charts = {}
        
        try:
            charts['overall_progress'] = self.create_overall_progress_chart(interviews)
        except Exception as e:
            print(f"⚠️ Genel gelişim grafiği hatası: {e}")
        
        try:
            charts['phase_comparison'] = self.create_phase_comparison_chart(interviews)
        except Exception as e:
            print(f"⚠️ Faz karşılaştırma grafiği hatası: {e}")
        
        try:
            charts['radar'] = self.create_radar_chart(interviews)
        except Exception as e:
            print(f"⚠️ Radar grafiği hatası: {e}")
        
        try:
            if len(interviews) >= 2:
                charts['improvement_trend'] = self.create_improvement_trend_chart(interviews)
        except Exception as e:
            print(f"⚠️ İyileşme trendi grafiği hatası: {e}")
        
        print(f"✅ {len([c for c in charts.values() if c])} grafik oluşturuldu!\n")
        
        return charts
