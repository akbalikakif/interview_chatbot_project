// Backend API URL'i - .env dosyasından veya varsayılan olarak
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// API çağrıları için yardımcı fonksiyon
const apiCall = async (endpoint, options = {}) => {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API Call Error:', error);
    throw error;
  }
};

// CV yükleme
export const uploadCV = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch(`${API_BASE_URL}/api/upload-cv`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('CV yükleme başarısız');
    }

    return await response.json();
  } catch (error) {
    console.error('CV Upload Error:', error);
    throw error;
  }
};

// Mülakat başlatma
export const startInterview = async (cvData = null) => {
  return await apiCall('/api/interview/start', {
    method: 'POST',
    body: JSON.stringify({
      has_cv: !!cvData,
      cv_data: cvData,
    }),
  });
};

// Sonraki soruyu getir
export const getNextQuestion = async (sessionId, questionNumber) => {
  return await apiCall(`/api/interview/question/${sessionId}/${questionNumber}`, {
    method: 'GET',
  });
};

// Kullanıcı cevabını gönder
export const submitAnswer = async (sessionId, questionNumber, answer) => {
  return await apiCall('/api/interview/answer', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      question_number: questionNumber,
      answer: answer,
    }),
  });
};

// Cevabı değerlendir
export const evaluateAnswer = async (sessionId, questionNumber) => {
  return await apiCall(`/api/interview/evaluate/${sessionId}/${questionNumber}`, {
    method: 'GET',
  });
};

// Final raporu al
export const getFinalReport = async (sessionId) => {
  return await apiCall(`/api/interview/report/${sessionId}`, {
    method: 'GET',
  });
};

// Raporu PDF olarak indir
export const downloadReportPDF = async (sessionId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/interview/report/${sessionId}/pdf`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error('PDF indirme başarısız');
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mulakat_raporu_${sessionId}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } catch (error) {
    console.error('PDF Download Error:', error);
    throw error;
  }
};

// Ses kaydını gönder (Speech-to-Text için)
export const sendAudioForTranscription = async (audioBlob, sessionId) => {
  const formData = new FormData();
  formData.append('audio', audioBlob);
  formData.append('session_id', sessionId);

  try {
    const response = await fetch(`${API_BASE_URL}/api/speech/transcribe`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Ses tanıma başarısız');
    }

    return await response.json();
  } catch (error) {
    console.error('Audio Transcription Error:', error);
    throw error;
  }
};

// Text-to-Speech için ses al
export const getQuestionAudio = async (questionText, sessionId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/speech/synthesize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: questionText,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      throw new Error('Ses sentezi başarısız');
    }

    const blob = await response.blob();
    return URL.createObjectURL(blob);
  } catch (error) {
    console.error('Text-to-Speech Error:', error);
    throw error;
  }
};