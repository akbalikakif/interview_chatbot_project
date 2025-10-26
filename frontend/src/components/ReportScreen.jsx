import React, { useState, useEffect } from 'react';
import { CheckCircle, Loader } from 'lucide-react';
import { evaluateAnswer } from '../services/api';

const EvaluationScreen = ({ onNext, questionNumber, sessionId }) => {
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadEvaluation = async () => {
      try {
        const response = await evaluateAnswer(sessionId, questionNumber);
        setEvaluation(response);
        setLoading(false);
      } catch (error) {
        console.error('Değerlendirme yükleme hatası:', error);
        // Hata durumunda varsayılan değerler
        setEvaluation({
          score: 7,
          max_score: 10,
          feedback: 'Değerlendirme yüklenirken bir hata oluştu.',
        });
        setLoading(false);
      }
    };

    loadEvaluation();
  }, [sessionId, questionNumber]);

  if (loading) {
    return (
      <div className="evaluation-screen">
        <div className="card evaluation-card">
          <div className="evaluation-loading">
            <Loader className="animate-spin" size={48} />
            <p>Cevabınız değerlendiriliyor...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="evaluation-screen">
      <div className="card evaluation-card">
        <div className="evaluation-header">
          <div className="evaluation-icon-circle">
            <CheckCircle className="text-white" size={40} />
          </div>
          <h2 className="evaluation-title">
            Soru {questionNumber} Değerlendirmesi
          </h2>
        </div>

        <div className="evaluation-body">
          <div className="score-item">
            <div className="score-header">
              <span className="score-label">Teknik Doğruluk</span>
              <span className="score-value">
                {evaluation.score}/{evaluation.max_score || 10}
              </span>
            </div>
            <div className="score-bar-background">
              <div 
                className="score-bar-foreground" 
                style={{ width: `${(evaluation.score / (evaluation.max_score || 10)) * 100}%` }}
              ></div>
            </div>
          </div>

          <p className="evaluation-feedback">
            {evaluation.feedback}
          </p>
        </div>

        <button
          onClick={onNext}
          className="next-button"
        >
          {questionNumber < 8 ? 'Sonraki Soru' : 'Mülakatı Tamamla'}
        </button>
      </div>
    </div>
  );
};

export default EvaluationScreen;