import React, { useState } from 'react';
import axios from 'axios';

import { useAuth } from '../context/AuthContext';

const StudentQuiz: React.FC = () => {
  const { user } = useAuth();
  const [accessCode, setAccessCode] = useState('');
  const [quizData, setQuizData] = useState<any>(null);
  const [answers, setAnswers] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [results, setResults] = useState<any>(null);

  const handleFetchQuiz = async () => {
    if (!accessCode.trim()) return;
    try {
      const res = await axios.get(`/api/v1/quiz/code/${accessCode}`);
      setQuizData(res.data);
      setAnswers(new Array(res.data.questions.length).fill(''));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Invalid access code');
    }
  };

  const handleAnswerChange = (index: number, value: string) => {
    const newAnswers = [...answers];
    newAnswers[index] = value;
    setAnswers(newAnswers);
  };

  const handleSubmit = async () => {
    if (answers.some((answer) => !answer.trim())) {
      if (!confirm('You have unanswered questions. Submit anyway?')) return;
    }
    setIsSubmitting(true);
    try {
      const res = await axios.post('/api/v1/quiz/submit', {
        access_code: accessCode,
        student_id: user?.id || 'unknown',
        answers,
      });
      setResults(res.data);
    } catch (err) {
      alert('Submission failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (results) {
    return (
      <div style={{ padding: '20px' }}>
        <h3>Quiz Results: {results.title}</h3>
        {results.results.map((result: any, index: number) => (
          <div key={index} className="quiz-result-card">
            <p><strong>Q: {result.question}</strong></p>
            <p>Your Answer: {result.student_answer}</p>
            <p>Result: <span style={{ color: result.result === 'pass' ? 'var(--success-color)' : 'var(--danger-color)', fontWeight: 'bold' }}>{result.result.toUpperCase()}</span></p>
          </div>
        ))}
        <button onClick={() => { setResults(null); setQuizData(null); setAccessCode(''); }}>Back</button>
      </div>
    );
  }

  if (quizData) {
    return (
      <div style={{ padding: '20px' }}>
        <h2>{quizData.title}</h2>
        <p className="muted">Course: {quizData.course_id}</p>
        <hr style={{ borderColor: 'var(--border-color)' }} />
        {quizData.questions.map((question: any, index: number) => (
          <div key={index} style={{ marginBottom: '20px' }}>
            <p><strong>Question {index + 1}:</strong> {question.question}</p>
            <textarea
              rows={4}
              value={answers[index]}
              onChange={(e) => handleAnswerChange(index, e.target.value)}
              placeholder="Type your answer here..."
            />
          </div>
        ))}
        <button onClick={handleSubmit} disabled={isSubmitting}>
          {isSubmitting ? 'Submitting...' : 'Submit Answers'}
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px', textAlign: 'center' }}>
      <h3>Enter Quiz Access Code</h3>
      <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginTop: '20px' }}>
        <input
          type="text"
          value={accessCode}
          onChange={(e) => setAccessCode(e.target.value.toUpperCase())}
          placeholder="e.g. AB1234"
          maxLength={6}
          style={{ fontSize: '18px', textAlign: 'center', width: '150px' }}
        />
        <button onClick={handleFetchQuiz}>Enter Quiz</button>
      </div>
    </div>
  );
};

export default StudentQuiz;
