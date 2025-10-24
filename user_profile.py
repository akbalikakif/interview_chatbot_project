"""
user_profile.py
Kullanıcı profil yönetimi ve mülakat geçmişi takibi
"""

import json
import os
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from speech_to_text import record_and_convert

# Kullanıcı veritabanı klasörü
USER_DATA_DIR = "user_data"
if not os.path.exists(USER_DATA_DIR):
    os.makedirs(USER_DATA_DIR)

class UserProfile:
    """Kullanıcı profili ve mülakat geçmişi yönetimi"""
    
    def __init__(self, username: str = None):
        """
        Args:
            username: Kullanıcı adı (None ise sesli olarak alınır)
        """
        self.username = username
        self.profile_path = None
        self.profile_data = None
        
        if username:
            self.load_or_create_profile(username)
    
    def ask_name_voice(self) -> Optional[str]:
        """Kullanıcıdan sesli olarak ismini alır"""
        print("\n" + "="*60)
        print("🎤 KULLANICI KAYDI")
        print("="*60)
        print("\nLütfen adınızı ve soyadınızı söyleyin...")
        print("Örnek: 'Ahmet Yılmaz' veya 'Ayşe Demir'\n")
        
        try:
            result = record_and_convert(question_number=None)
            
            if result and result.get('transcript'):
                name = result['transcript'].strip()
                
                # İsim doğrulama
                print(f"\n✅ Algılanan isim: '{name}'")
                print("\nBu isim doğru mu? (Evet için Enter, Hayır için 'h' yazın)")
                
                confirmation = input(">>> ").strip().lower()
                
                if confirmation in ['h', 'hayır', 'hayir', 'no']:
                    print("\n📝 Lütfen isminizi yazın:")
                    name = input(">>> ").strip()
                
                if name:
                    print(f"\n🎉 Hoş geldiniz, {name}!")
                    return name
            
            # Ses algılanamazsa manuel giriş
            print("\n⚠️ Ses algılanamadı. Lütfen isminizi yazın:")
            name = input(">>> ").strip()
            
            if name:
                return name
            
            return None
            
        except Exception as e:
            print(f"\n❌ Hata: {e}")
            print("📝 Lütfen isminizi yazın:")
            name = input(">>> ").strip()
            return name if name else None
    
    def load_or_create_profile(self, username: str) -> Dict:
        """Kullanıcı profilini yükler veya oluşturur"""
        self.username = username
        
        # Dosya adını temizle (özel karakterleri kaldır)
        safe_username = "".join(c for c in username if c.isalnum() or c in (' ', '_', '-')).strip()
        safe_username = safe_username.replace(' ', '_')
        
        self.profile_path = os.path.join(USER_DATA_DIR, f"{safe_username}.json")
        
        # Profil varsa yükle
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, 'r', encoding='utf-8') as f:
                    self.profile_data = json.load(f)
                
                print(f"\n📂 Profil yüklendi: {username}")
                print(f"   Toplam mülakat sayısı: {len(self.profile_data.get('interviews', []))}")
                
                if self.profile_data.get('interviews'):
                    last_interview = self.profile_data['interviews'][-1]
                    last_date = last_interview.get('date', 'Bilinmiyor')
                    last_score = last_interview.get('overall_score', 0)
                    print(f"   Son mülakat: {last_date} - Skor: {last_score:.1f}/10")
            
            except json.JSONDecodeError:
                # JSON bozuksa yedekle ve yeni profil oluştur
                print(f"\n⚠️ Profil dosyası bozuk. Yedekleniyor ve yeni profil oluşturuluyor...")
                backup_path = self.profile_path.replace('.json', '_backup.json')
                if os.path.exists(self.profile_path):
                    os.rename(self.profile_path, backup_path)
                    print(f"   Yedek: {backup_path}")
                
                # Yeni profil oluştur
                self.profile_data = {
                    'username': username,
                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'interviews': []
                }
                self._save_profile()
                print(f"   ✅ Yeni profil oluşturuldu")
        else:
            # Yeni profil oluştur
            self.profile_data = {
                'username': username,
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'interviews': []
            }
            self._save_profile()
            print(f"\n✨ Yeni profil oluşturuldu: {username}")
        
        return self.profile_data
    
    def _convert_to_json_serializable(self, obj):
        """Numpy tiplerini Python tiplerine dönüştürür"""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self._convert_to_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_json_serializable(item) for item in obj]
        else:
            return obj
    
    def add_interview_result(self, interview_data: Dict):
        """
        Mülakat sonucunu profile ekler
        
        Args:
            interview_data: Mülakat verileri (overall_score, content_score, audio_score, vb.)
        """
        
        # Numpy tiplerini Python tiplerine dönüştür
        interview_data = self._convert_to_json_serializable(interview_data)
        
        # Mülakat verisi
        interview_entry = {
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'overall_score': interview_data.get('overall_score', 0),
            'content_score': interview_data.get('content_score', 0),
            'audio_score': interview_data.get('audio_score', 0),
            'phase_scores': interview_data.get('phase_scores', {}),
            'question_count': interview_data.get('question_count', 0),
            'answers': interview_data.get('answers', [])
        }
        
        self.profile_data['interviews'].append(interview_entry)
        self._save_profile()
        
        print(f"\n💾 Mülakat sonucu kaydedildi!")
        print(f"   Toplam mülakat: {len(self.profile_data['interviews'])}")
    
    def _save_profile(self):
        """Profili JSON dosyasına kaydeder"""
        with open(self.profile_path, 'w', encoding='utf-8') as f:
            json.dump(self.profile_data, f, ensure_ascii=False, indent=2)
    
    def get_interview_history(self) -> List[Dict]:
        """Mülakat geçmişini döndürür"""
        if not self.profile_data:
            return []
        return self.profile_data.get('interviews', [])
    
    def get_statistics(self) -> Dict:
        """Kullanıcı istatistiklerini hesaplar"""
        interviews = self.get_interview_history()
        
        if not interviews:
            return {
                'total_interviews': 0,
                'average_score': 0,
                'best_score': 0,
                'worst_score': 0,
                'improvement_rate': 0
            }
        
        scores = [i.get('overall_score', 0) for i in interviews]
        
        # İlerleme oranı (son 3 mülakat vs önceki 3 mülakat)
        improvement_rate = 0
        if len(interviews) >= 6:
            recent_avg = sum(scores[-3:]) / 3
            old_avg = sum(scores[-6:-3]) / 3
            improvement_rate = ((recent_avg - old_avg) / old_avg) * 100 if old_avg > 0 else 0
        elif len(interviews) >= 2:
            improvement_rate = ((scores[-1] - scores[0]) / scores[0]) * 100 if scores[0] > 0 else 0
        
        return {
            'total_interviews': len(interviews),
            'average_score': sum(scores) / len(scores),
            'best_score': max(scores),
            'worst_score': min(scores),
            'improvement_rate': improvement_rate,
            'latest_score': scores[-1] if scores else 0
        }
    
    def get_phase_performance(self) -> Dict:
        """Faz bazında performans analizi"""
        interviews = self.get_interview_history()
        
        if not interviews:
            return {}
        
        phase_data = {
            'kişisel': [],
            'teknik': [],
            'senaryo': []
        }
        
        for interview in interviews:
            phase_scores = interview.get('phase_scores', {})
            for phase, score in phase_scores.items():
                if phase in phase_data:
                    phase_data[phase].append(score)
        
        # Ortalama hesapla
        phase_averages = {}
        for phase, scores in phase_data.items():
            if scores:
                phase_averages[phase] = sum(scores) / len(scores)
            else:
                phase_averages[phase] = 0
        
        return phase_averages

def get_or_create_user() -> UserProfile:
    """Kullanıcı profilini alır veya oluşturur"""
    print("\n" + "="*60)
    print("👤 KULLANICI GİRİŞİ")
    print("="*60)
    
    # Mevcut kullanıcıları listele
    existing_users = []
    if os.path.exists(USER_DATA_DIR):
        for filename in os.listdir(USER_DATA_DIR):
            if filename.endswith('.json'):
                username = filename[:-5].replace('_', ' ')
                existing_users.append(username)
    
    if existing_users:
        print("\n📋 Kayıtlı kullanıcılar:")
        for i, user in enumerate(existing_users, 1):
            print(f"   {i}. {user}")
        
        print("\n🔹 Mevcut kullanıcı olarak devam etmek için numara girin")
        print("🔹 Yeni kullanıcı için 'y' yazın")
        print("🔹 Sesli kayıt için 's' yazın")
        
        choice = input("\n>>> ").strip().lower()
        
        # Numara seçimi
        if choice.isdigit() and 1 <= int(choice) <= len(existing_users):
            username = existing_users[int(choice) - 1]
            return UserProfile(username)
        
        # Sesli kayıt
        elif choice == 's':
            profile = UserProfile()
            username = profile.ask_name_voice()
            if username:
                return UserProfile(username)
            else:
                print("❌ İsim alınamadı. Varsayılan kullanıcı: 'Misafir'")
                return UserProfile("Misafir")
        
        # Yeni kullanıcı
        elif choice == 'y':
            print("\n📝 Yeni kullanıcı adı:")
            username = input(">>> ").strip()
            if username:
                return UserProfile(username)
    
    # İlk kullanıcı - manuel veya sesli kayıt
    print("\n🎤 İlk kullanıcı kaydı")
    print("   🔹 Sesli kayıt için 's' yazın")
    print("   🔹 Manuel girmek için direkt isminizi yazın")
    
    choice = input("\n>>> ").strip()
    
    if choice.lower() == 's':
        # Sesli kayıt
        profile = UserProfile()
        username = profile.ask_name_voice()
        if username:
            return UserProfile(username)
    elif choice:
        # Manuel giriş (direkt isim yazıldı)
        print(f"\n✅ Kullanıcı adı: '{choice}'")
        return UserProfile(choice)
    
    # Fallback
    print("❌ İsim alınamadı. Varsayılan kullanıcı: 'Misafir'")
    return UserProfile("Misafir")
