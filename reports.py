"""
reports.py
Mülakat sonuçlarını analiz edip detaylı rapor oluşturan modül
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any

class ReportGenerator:
    """Mülakat raporları oluşturan sınıf"""
    
    def __init__(self):
        self.reports_dir = "reports"
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)
    
    def generate_interview_report(self, interview_history: List[Dict], candidate_name: str = "Aday") -> str:
        """Mülakat geçmişinden detaylı rapor oluşturur"""
        
        report_data = {
            "candidate_name": candidate_name,
            "interview_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_questions": len(interview_history),
            "scores": self._calculate_scores(interview_history),
            "phases": self._analyze_phases(interview_history),
            "recommendations": self._generate_recommendations(interview_history),
            "detailed_analysis": self._detailed_question_analysis(interview_history)
        }
        
        # JSON raporu kaydet
        report_filename = f"interview_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join(self.reports_dir, report_filename)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        # İnsan okunabilir rapor oluştur
        human_readable_report = self._create_human_readable_report(report_data)
        human_report_path = os.path.join(self.reports_dir, f"human_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        with open(human_report_path, 'w', encoding='utf-8') as f:
            f.write(human_readable_report)
        
        print(f"Rapor oluşturuldu: {report_path}")
        print(f"İnsan okunabilir rapor: {human_report_path}")
        
        return human_readable_report
    
    def _calculate_scores(self, history: List[Dict]) -> Dict:
        """Genel puanları hesaplar"""
        if not history:
            return {"average": 0, "total": 0}
        
        scores = []
        for h in history:
            if 'analysis' in h and 'score' in h['analysis']:
                scores.append(h['analysis']['score'])
        
        if not scores:
            return {"average": 0, "total": 0}
        
        return {
            "average": round(sum(scores) / len(scores), 1),
            "total": sum(scores),
            "max": max(scores),
            "min": min(scores),
            "count": len(scores)
        }
    
    def _analyze_phases(self, history: List[Dict]) -> Dict:
        """Faz bazında analiz yapar"""
        phase_scores = {}
        
        for h in history:
            phase = h.get('kategori', 'bilinmeyen')
            if phase not in phase_scores:
                phase_scores[phase] = []
            
            if 'analysis' in h and 'score' in h['analysis']:
                phase_scores[phase].append(h['analysis']['score'])
        
        # Her faz için ortalama hesapla
        phase_averages = {}
        for phase, scores in phase_scores.items():
            if scores:
                phase_averages[phase] = round(sum(scores) / len(scores), 1)
        
        return phase_averages
    
    def _generate_recommendations(self, history: List[Dict]) -> List[str]:
        """Aday için öneriler oluşturur"""
        recommendations = []
        
        # Genel performans analizi
        scores = [h.get('analysis', {}).get('score', 0) for h in history if 'analysis' in h]
        if not scores:
            return ["Yeterli veri bulunamadı"]
        
        avg_score = sum(scores) / len(scores)
        
        if avg_score >= 8:
            recommendations.append("Mükemmel performans! Teknik bilgi ve iletişim becerileri çok güçlü.")
            recommendations.append("Bu seviyede bir aday için zorlu projeler ve liderlik rolleri önerilir.")
        elif avg_score >= 6:
            recommendations.append("İyi performans. Bazı alanlarda gelişim fırsatları var.")
            recommendations.append("Teknik becerileri güçlendirmek için ek eğitimler önerilir.")
        elif avg_score >= 4:
            recommendations.append("Orta seviye performans. Temel beceriler mevcut ancak gelişim gerekiyor.")
            recommendations.append("Mentorluk ve sürekli eğitim programları önerilir.")
        else:
            recommendations.append("Performans düşük. Temel becerilerin geliştirilmesi gerekiyor.")
            recommendations.append("Kapsamlı eğitim programı ve yakın mentorluk önerilir.")
        
        # Faz bazında öneriler
        phase_scores = self._analyze_phases(history)
        for phase, score in phase_scores.items():
            if score < 5:
                if phase == "kişisel":
                    recommendations.append("Kişisel iletişim becerilerini geliştirmek için sunum ve toplantı pratikleri önerilir.")
                elif phase == "teknik":
                    recommendations.append("Teknik bilgi eksikliği var. İlgili teknolojilerde derinlemesine çalışma önerilir.")
                elif phase == "senaryo":
                    recommendations.append("Problem çözme becerilerini geliştirmek için case study çalışmaları önerilir.")
        
        return recommendations
    
    def _detailed_question_analysis(self, history: List[Dict]) -> List[Dict]:
        """Her soru için detaylı analiz"""
        detailed = []
        
        for i, h in enumerate(history, 1):
            question_analysis = {
                "question_number": i,
                "question": h.get('soru', 'Bilinmeyen soru'),
                "category": h.get('kategori', 'Bilinmeyen'),
                "answer": h.get('answer', 'Cevap bulunamadı'),
                "score": h.get('analysis', {}).get('score', 0),
                "feedback": h.get('analysis', {}).get('feedback', 'Değerlendirme bulunamadı'),
                "difficulty": h.get('difficulty_level', 'Bilinmeyen')
            }
            detailed.append(question_analysis)
        
        return detailed
    
    def _create_human_readable_report(self, report_data: Dict) -> str:
        """İnsan okunabilir rapor oluşturur"""
        report = f"""
=== MÜLAKAT DEĞERLENDİRME RAPORU ===

Aday: {report_data['candidate_name']}
Tarih: {report_data['interview_date']}
Toplam Soru: {report_data['total_questions']}

=== GENEL PERFORMANS ===
Ortalama Puan: {report_data['scores']['average']}/10
Toplam Puan: {report_data['scores']['total']}
En Yüksek: {report_data['scores']['max']}/10
En Düşük: {report_data['scores']['min']}/10

=== FAZ BAZINDA PERFORMANS ===
"""
        
        for phase, score in report_data['phases'].items():
            report += f"{phase.upper()}: {score}/10\n"
        
        report += "\n=== ÖNERİLER ===\n"
        for i, rec in enumerate(report_data['recommendations'], 1):
            report += f"{i}. {rec}\n"
        
        report += "\n=== DETAYLI SORU ANALİZİ ===\n"
        for detail in report_data['detailed_analysis']:
            report += f"""
Soru {detail['question_number']} ({detail['category']}):
Soru: {detail['question']}
Cevap: {detail['answer'][:100]}{'...' if len(detail['answer']) > 100 else ''}
Puan: {detail['score']}/10
Zorluk: {detail['difficulty']}
Geri Bildirim: {detail['feedback']}
---
"""
        
        return report

def generate_final_report(interview_handler) -> str:
    """InterviewHandler'dan rapor oluşturur"""
    generator = ReportGenerator()
    return generator.generate_interview_report(interview_handler.history)