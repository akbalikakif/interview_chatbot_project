import React, { useState, useEffect, useRef } from 'react';
import { Mic, Volume2, Ear, Brain, AlertCircle } from 'lucide-react';
import EvaluationScreen from './EvaluationScreen';
import { startInterview, getNextQuestion, submitAnswer, sendAudioForTranscription, getQuestionAudio } from '../services/api';

const InterviewScreen = ({ onComplete, cvData, hasCv }) => {
  const [sessionId, setSessionId] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(1);
  const [aiSpeaking, setAiSpeaking] = useState(true);
  const [userSpeaking, setUserSpeaking] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [showEvaluation, setShowEvaluation] = useState(false);
  const [questionText, setQuestionText] = useState("Soru yükleniyor...");
  const [audioURL, setAudioURL] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioElementRef = useRef(null);

  // Mülakat başlatma ve ilk soruyu getirme
  useEffect(() => {
    const initInterview = async () => {
      try {
        // Backend'e mülakat başlatma isteği gönder
        const response = await startInterview(cvData);
        setSessionId(response.session_id);
        
        // İlk soruyu al
        const questionData = await getNextQuestion(response.session_id, 1);
        setQuestionText(questionData.question);
        
        // Soruyu sesli oku (Text-to-Speech)
        try {
          const audio = await getQuestionAudio(questionData.question, response.session_id);
          setAudioURL(audio);
          
          // Ses oynatma
          const audioElement = new Audio(audio);
          audioElementRef.current = audioElement;
          audioElement.play();
          
          audioElement.onended = () => {
            setAiSpeaking(false);
          };
        } catch (audioError) {
          console.warn('Text-to-Speech hatası:', audioError);
          // TTS çalışmazsa 3 saniye bekle
          setTimeout(() => {
            setAiSpeaking(false);
          }, 3000);
        }
      } catch (error) {
        console.error('Mülakat başlatma hatası:', error);
        setErrorMessage('Mülakat başlatılırken bir hata oluştu.');
        setQuestionText("Soru yüklenirken bir hata oluştu.");
        setAiSpeaking(false);
        setShowError(true);
      }
    };

    initInterview();

    // Cleanup
    return () => {
      if (audioElementRef.current) {
        audioElementRef.current.pause();
        audioElementRef.current = null;
      }
    };
  }, [cvData]);

  // Mikrofon erişimi ayarlama
  useEffect(() => {
    const setupMicrophone = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorderRef.current = new MediaRecorder(stream);

        mediaRecorderRef.current.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };
      } catch (error) {
        console.error('Mikrofon erişim hatası:', error);
        setErrorMessage('Mikrofon erişimi reddedildi. Lütfen tarayıcı ayarlarından mikrofon iznini kontrol edin.');
        setShowError(true);
      }
    };

    setupMicrophone();

    // Cleanup
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const handleMicClick = () => {
    if (!mediaRecorderRef.current) {
      setErrorMessage('Mikrofon hazır değil. Lütfen sayfayı yenileyip tekrar deneyin.');
      setShowError(true);
      return;
    }

    setUserSpeaking(true);
    setShowError(false);
    audioChunksRef.current = [];
    
    // Ses kaydını başlat
    mediaRecorderRef.current.start();
    
    // 4 saniye sonra kaydı durdur
    setTimeout(() => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
    }, 4000);

    mediaRecorderRef.current.onstop = async () => {
      setUserSpeaking(false);
      setAnalyzing(true);
      
      try {
        // Ses dosyasını oluştur
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        // Backend'e gönder ve metne çevir
        const transcriptionResponse = await sendAudioForTranscription(audioBlob, sessionId);
        
        // Cevabı backend'e gönder
        await submitAnswer(sessionId, currentQuestion, transcriptionResponse.text);
        
        setTimeout(() => {
          setAnalyzing(false);
          
          // 8 soru tamamlandıysa rapor ekranına geç
          if (currentQuestion >= 8) {
            onComplete(sessionId);
          } else {
            // Sonraki soruya geç
            loadNextQuestion();
          }
        }, 1000);
      } catch (error) {
        console.error('Cevap gönderme hatası:', error);
        setAnalyzing(false);
        setErrorMessage('Cevabınız işlenirken bir hata oluştu. Lütfen tekrar deneyin.');
        setShowError(true);
      }
    };
  };

  const loadNextQuestion = async () => {
    try {
      const nextQuestionNumber = currentQuestion + 1;
      setCurrentQuestion(nextQuestionNumber);
      setAiSpeaking(true);
      
      // Backend'den sonraki soruyu al
      const questionData = await getNextQuestion(sessionId, nextQuestionNumber);
      setQuestionText(questionData.question);
      
      // Soruyu sesli oku
      try {
        const audio = await getQuestionAudio(questionData.question, sessionId);
        setAudioURL(audio);
        
        const audioElement = new Audio(audio);
        audioElementRef.current = audioElement;
        audioElement.play();
        
        audioElement.onended = () => {
          setAiSpeaking(false);
        };
      } catch (audioError) {
        console.warn('Text-to-Speech hatası:', audioError);
        setTimeout(() => {
          setAiSpeaking(false);
        }, 3000);
      }
    } catch (error) {
      console.error('Soru yükleme hatası:', error);
      setErrorMessage('Sonraki soru yüklenirken bir hata oluştu.');
      setAiSpeaking(false);
      setShowError(true);
    }
  };

  const handleRepeat = async () => {
    setAiSpeaking(true);
    setShowError(false);
    
    // Mevcut soruyu tekrar sesli oku
    if (audioURL) {
      try {
        const audioElement = new Audio(audioURL);
        audioElementRef.current = audioElement;
        audioElement.play();
        
        audioElement.onended = () => {
          setAiSpeaking(false);
        };
      } catch (error) {
        console.warn('Ses tekrarı hatası:', error);
        setTimeout(() => {
          setAiSpeaking(false);
        }, 3000);
      }
    } else {
      // Ses yoksa sadece bekleme
      setTimeout(() => {
        setAiSpeaking(false);
      }, 3000);
    }
  };

  const handleNextQuestion = () => {
    setShowEvaluation(false);
    if (currentQuestion < 8) {
      loadNextQuestion();
    } else {
      onComplete(sessionId);
    }
  };

  if (showEvaluation) {
    return <EvaluationScreen onNext={handleNextQuestion} questionNumber={currentQuestion} sessionId={sessionId} />;
  }

  return (
    <div className="interview-screen">
      <div className="card interview-card">
        <div className="question-counter">
          Soru {currentQuestion} / 8
        </div>

        <div className="interview-avatar-wrapper">
          <div className="avatar-relative">
            <div className={`interview-avatar-circle ${aiSpeaking ? 'animate-pulse' : ''}`}>
              <div className="avatar-emoji large">👨‍💼</div>
            </div>
            
            {aiSpeaking && (
              <div className="avatar-icon volume">
                <Volume2 className="animate-bounce" size={32} />
              </div>
            )}
            
            {userSpeaking && (
              <div className="avatar-icon ear">
                <Ear className="animate-pulse" size={32} />
              </div>
            )}
            
            {analyzing && (
              <div className="avatar-icon brain">
                <Brain className="animate-bounce" size={32} />
              </div>
            )}
          </div>
        </div>

        <div className="interview-status-box">
          {aiSpeaking && (
            <div className="status-bubble ai-speaking">
              <p className="question-text">{questionText}</p>
              <div className="status-line">
                <Volume2 className="animate-pulse" size={20} />
                <span>AI konuşuyor...</span>
              </div>
            </div>
          )}

          {!aiSpeaking && !userSpeaking && !analyzing && (
            <div className="status-bubble mic-ready">
              <p className="mic-prompt">
                Cevabınızı mikrofona söyleyin.
              </p>
              <button
                onClick={handleMicClick}
                className="mic-button"
                disabled={!sessionId}
              >
                <Mic size={32} />
              </button>
            </div>
          )}

          {userSpeaking && (
            <div className="status-bubble user-speaking">
              <div className="status-line">
                <Mic className="animate-pulse" size={24} />
                <span>Sizi dinliyorum...</span>
              </div>
            </div>
          )}

          {analyzing && (
            <div className="status-bubble analyzing">
              <div className="status-line">
                <Brain className="animate-spin" size={24} />
                <span>🤔 Düşünüyor...</span>
              </div>
            </div>
          )}

          {showError && (
            <div className="status-bubble error">
              <AlertCircle size={20} />
              <span>{errorMessage || 'Bir hata oluştu.'}</span>
            </div>
          )}
        </div>

        {!aiSpeaking && !userSpeaking && !analyzing && (
          <div className="repeat-button-wrapper">
            <button
              onClick={handleRepeat}
              className="repeat-button"
            >
              Soruyu tekrar dinle
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default InterviewScreen;