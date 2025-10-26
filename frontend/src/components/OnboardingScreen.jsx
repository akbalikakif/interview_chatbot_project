import React, { useState } from 'react';
import { FileText, CheckCircle, XCircle, Loader, AlertCircle } from 'lucide-react';
import { uploadCV } from '../services/api';

const OnboardingScreen = ({ onStartInterview }) => {
  const [cvFile, setCvFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [canStart, setCanStart] = useState(true);
  const [cvData, setCvData] = useState(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Not: Dosya formatı kontrolü .docx için basitleştirildi
    const validExtensions = ['.pdf', '.docx', '.txt'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

    if (validExtensions.includes(fileExtension)) {
      setCvFile(file);
      setUploadStatus('success');
      setIsAnalyzing(true);
      setCanStart(false);

      try {
        // Backend'e CV'yi gönder
        const response = await uploadCV(file);
        setCvData(response);
        
        setTimeout(() => {
          setIsAnalyzing(false);
          setAnalysisComplete(true);
          setCanStart(true);
        }, 1000);
      } catch (error) {
        console.error('CV yükleme hatası:', error);
        setUploadStatus('error');
        setIsAnalyzing(false);
        setCanStart(true);
        setCvFile(null);
        setCvData(null);
      }
    } else {
      setUploadStatus('error');
      setCvFile(null);
      setAnalysisComplete(false);
      setCanStart(true);
    }
  };

  return (
    <div className="onboarding-screen">
      <div className="card onboarding-card">
        <div className="onboarding-header">
          <div className="avatar-wrapper">
            <div className="avatar-circle">
              <div className="avatar-emoji">👨‍💼</div>
            </div>
          </div>
          
          <h1 className="main-title">
            Hazırsan mülakata başlayalım!
          </h1>
          <p className="subtitle">
            AI destekli mülakat deneyiminiz için hazırız.
          </p>
        </div>

        <div className="upload-section">
          <div className="upload-title-wrapper">
            <FileText className="text-indigo-600" size={24} />
            <h2 className="upload-title">CV Yükleme</h2>
          </div>
          
          <p className="upload-info">
            Kabul Edilen Formatlar: <span>PDF, DOCX, TXT</span>
          </p>

          <label className="block">
            <input
              type="file"
              onChange={handleFileUpload}
              accept=".pdf,.docx,.txt"
              className="file-input"
            />
          </label>

          {uploadStatus === 'success' && (
            <div className="status-message success">
              <CheckCircle size={20} />
              <span>✅ CV başarıyla eklendi.</span>
            </div>
          )}
          
          {uploadStatus === 'error' && (
            <div className="status-message error">
              <XCircle size={20} />
              <span>❌ Hata: Desteklenmeyen dosya formatı veya yükleme başarısız.</span>
            </div>
          )}

          {isAnalyzing && (
            <div className="status-message info">
              <Loader className="animate-spin" size={20} />
              <span>⏳ CV'niz analiz ediliyor...</span>
            </div>
          )}

          {analysisComplete && (
            <div className="status-message info-dark">
              <CheckCircle size={20} />
              <span>🎯 Mülakatınız CV'nizdeki teknolojilere göre özelleştirilecek.</span>
            </div>
          )}

          {!cvFile && !isAnalyzing && (
            <div className="status-message note">
              <AlertCircle size={20} />
              <span>CV yüklemeden de mülakata başlayabilirsiniz. Genel sorularla devam edilecek.</span>
            </div>
          )}
        </div>

        <button
          onClick={() => onStartInterview(cvData)}
          disabled={!canStart}
          className="start-button"
        >
          Mülakata Başla
        </button>
        
        {canStart && (
          <p className="button-subtitle">
            {cvFile ? '📄 Özelleştirilmiş mülakat' : '📋 Genel mülakat'}
          </p>
        )}
      </div>
    </div>
  );
};

export default OnboardingScreen;