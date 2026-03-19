import React, { useEffect, useState } from 'react';
import axios from 'axios';

import { useCourse } from '../App';

const TeacherQuiz: React.FC = () => {
  const { currentCourse } = useCourse();
  const [documents, setDocuments] = useState<string[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);
  const [topic, setTopic] = useState('');
  const [difficulty, setDifficulty] = useState<'Easy' | 'Medium' | 'Hard'>('Medium');
  const [quizDraft, setQuizDraft] = useState<any[]>([]);
  const [quizTitle, setQuizTitle] = useState('');
  const [accessCode, setAccessCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (currentCourse) {
      fetchDocuments();
      setSelectedFiles([]);
      setQuizDraft([]);
      setAccessCode('');
    }
  }, [currentCourse]);

  const fetchDocuments = async () => {
    if (!currentCourse) return;
    try {
      const res = await axios.get(`/api/v1/quiz/documents?course_id=${currentCourse.course_id}`);
      setDocuments(res.data.files);
    } catch (err) {
      console.error('Failed to fetch docs', err);
    }
  };

  const handleGenerate = async () => {
    if (!currentCourse) return;
    if (selectedFiles.length === 0) return alert('Please select at least one file');
    setIsLoading(true);
    try {
      const res = await axios.post('/api/v1/quiz/generate', {
        topic,
        course_id: currentCourse.course_id,
        selected_files: selectedFiles,
        difficulty,
      });
      setQuizDraft(res.data.questions);
    } catch (err) {
      alert('Generation failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDraftChange = (index: number, field: 'question' | 'grading_criteria', value: string) => {
    const updatedDraft = [...quizDraft];
    updatedDraft[index][field] = value;
    setQuizDraft(updatedDraft);
  };

  const handleSave = async () => {
    if (!currentCourse) return;
    try {
      const res = await axios.post('/api/v1/quiz/create', {
        title: quizTitle || `${topic} Quiz`,
        course_id: currentCourse.course_id,
        source_files: selectedFiles,
        questions: quizDraft,
      });
      setAccessCode(res.data.access_code);
      alert('Quiz created successfully!');
    } catch (err) {
      alert('Save failed');
    }
  };

  if (!currentCourse) return <div style={{ padding: '20px' }}>Please select a course first.</div>;

  return (
    <div style={{ padding: '20px' }}>
      <div className="quiz-panel" style={{ marginBottom: '20px' }}>
        Active course: <strong>{currentCourse.course_name} ({currentCourse.course_id})</strong>
      </div>

      <h3>Teacher: Create a Quiz</h3>

      <div className="quiz-grid">
        <div className="quiz-panel">
          <h4>Available Documents</h4>
          {documents.length === 0 ? <p className="muted">No indexed documents found for this course.</p> : documents.map((doc) => (
            <div key={doc}>
              <input
                type="checkbox"
                checked={selectedFiles.includes(doc)}
                onChange={(e) => {
                  if (e.target.checked) setSelectedFiles([...selectedFiles, doc]);
                  else setSelectedFiles(selectedFiles.filter((file) => file !== doc));
                }}
              />{' '}
              {doc}
            </div>
          ))}
        </div>

        <div className="quiz-panel">
          <h4>Settings</h4>
          <label>Topic:</label>
          <input placeholder="e.g. SQL Basics" value={topic} onChange={(e) => setTopic(e.target.value)} style={{ marginBottom: '10px' }} />
          <label>Difficulty:</label>
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value as 'Easy' | 'Medium' | 'Hard')} style={{ marginBottom: '10px' }}>
            <option value="Easy">Easy</option>
            <option value="Medium">Medium</option>
            <option value="Hard">Hard</option>
          </select>
          <button onClick={handleGenerate} disabled={isLoading || documents.length === 0} style={{ width: '100%' }}>
            {isLoading ? 'Generating...' : 'AI Generate Questions'}
          </button>
        </div>
      </div>

      {quizDraft.length > 0 && (
        <div style={{ marginTop: '20px', borderTop: '2px solid var(--primary-color)', paddingTop: '20px' }}>
          <h4>Preview & Save</h4>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ fontWeight: 'bold' }}>Quiz Title:</label>
            <input
              placeholder="Quiz Title"
              value={quizTitle}
              onChange={(e) => setQuizTitle(e.target.value)}
              style={{ marginTop: '5px' }}
            />
          </div>
          {quizDraft.map((question, idx) => (
            <div key={idx} className="quiz-draft-card">
              <div style={{ marginBottom: '10px' }}>
                <label style={{ fontWeight: 'bold' }}>Q{idx + 1}:</label>
                <textarea
                  value={question.question}
                  onChange={(e) => handleDraftChange(idx, 'question', e.target.value)}
                  style={{ marginTop: '5px' }}
                  rows={2}
                />
              </div>
              <div>
                <label style={{ fontWeight: 'bold', fontSize: '0.9rem' }}>Grading Criteria:</label>
                <textarea
                  value={question.grading_criteria}
                  onChange={(e) => handleDraftChange(idx, 'grading_criteria', e.target.value)}
                  style={{ marginTop: '5px', fontSize: '0.9rem' }}
                  rows={2}
                />
              </div>
            </div>
          ))}
          <button onClick={handleSave} style={{ width: '100%', background: 'var(--success-color)', color: '#03131f' }}>
            Finalize & Save Quiz
          </button>
        </div>
      )}

      {accessCode && (
        <div className="success-box" style={{ marginTop: '20px' }}>
          <p style={{ margin: 0 }}>Quiz Created! Share this code with students:</p>
          <strong style={{ fontSize: '32px', color: 'var(--success-color)', letterSpacing: '4px' }}>{accessCode}</strong>
        </div>
      )}
    </div>
  );
};

export default TeacherQuiz;
