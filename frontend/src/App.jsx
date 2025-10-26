import React, { useState } from 'react';
import OnboardingScreen from './components/OnboardingScreen';
import InterviewScreen from './components/InterviewScreen';
import ReportScreen from './components/ReportScreen';
import './App.css';

export default function App() {
  // 1. UYGULAMANIN ANA HAFIZASI (STATE)
  const [currentScreen, setCurrentScreen] = useState('onboarding'); // Hangi ekranda olduğumuzu tutar
  const [hasCv, setHasCv] = useState(false);
  const [countdown, setCountdown] = useState(3);
  const [sessionId, setSessionId] = useState(null);
  const [cvData, setCvData] = useState(null);

  // 2. MANTIKSAL FONKSİYONLAR
  // Bu fonksiyon, OnboardingScreen'e 'prop' olarak gönderilecek
  const handleStartInterview = (uploadedCvData) => {
    setCvData(uploadedCvData); // Backend'den dönen CV verisini kaydet
    setHasCv(!!uploadedCvData); // cvData varsa true, yoksa false yap
    setCurrentScreen('countdown'); // Önce geri sayım ekranına geç
    setCountdown(3);
    
    // Geri sayım başlat
    const countdownInterval = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(countdownInterval);
          setCurrentScreen('interview'); // 0'a ulaşınca mülakata başla
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };
  
  const handleCompleteInterview = (interviewSessionId) => {
    setSessionId(interviewSessionId); // Session ID'yi kaydet
    setCurrentScreen('report'); // Rapor ekranına geç
  };

  // 3. GÖRÜNÜM (JSX) - HANGİ EKRANI GÖSTERECEĞİNE KARAR VEREN YER
  return (
    <div className="main-container"> {/* Tüm uygulamayı saran bir div */}
      
      {/* Bu, KOŞULLU RENDERİNG (Conditional Rendering) yöntemidir */}

      {currentScreen === 'onboarding' && (
        <OnboardingScreen onStartInterview={handleStartInterview} />
      )}
      
      {currentScreen === 'countdown' && (
        <div className="countdown-screen">
          <div className="card countdown-card">
            <div className="countdown-content">
              <h2 className="countdown-title">Mülakat Başlıyor!</h2>
              <div className="countdown-number">{countdown}</div>
              <p className="countdown-text">Hazır olun...</p>
            </div>
          </div>
        </div>
      )}
      
      {currentScreen === 'interview' && (
        <InterviewScreen 
          onComplete={handleCompleteInterview} 
          cvData={cvData}
          hasCv={hasCv}
        />
      )}
      
      {currentScreen === 'report' && (
        <ReportScreen sessionId={sessionId} />
      )}

    </div>
  );
}