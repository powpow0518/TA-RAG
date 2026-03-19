import React from 'react';

import { useCourse } from '../App';
import StudentQuiz from '../components/StudentQuiz';
import TeacherQuiz from '../components/TeacherQuiz';
import { useAuth } from '../context/AuthContext';

const QuizPage: React.FC = () => {
  const { user } = useAuth();
  const { currentCourse } = useCourse();
  const [activeTab, setActiveTab] = React.useState<'teacher' | 'student'>('student');

  if (!user) return <p>Please login to see quizzes.</p>;
  if (!currentCourse) return <div style={{ padding: '20px' }}>Please select a course first.</div>;

  const content = (
    <>
      <div className="quiz-banner" style={{ marginBottom: '20px', textAlign: 'center' }}>
        Active quiz course: <strong>{currentCourse.course_name} ({currentCourse.course_id})</strong>
      </div>
      <div className="quiz-content">
        {activeTab === 'teacher' ? <TeacherQuiz /> : <StudentQuiz />}
      </div>
    </>
  );

  if (user.role === 'admin') {
    return (
      <div className="quiz-container">
        <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.75rem' }}>
          <button
            style={{ opacity: activeTab === 'student' ? 1 : 0.68 }}
            onClick={() => setActiveTab('student')}
          >
            Student Quiz
          </button>
          <button
            style={{ opacity: activeTab === 'teacher' ? 1 : 0.68 }}
            onClick={() => setActiveTab('teacher')}
          >
            Teacher Quiz
          </button>
        </div>
        {content}
      </div>
    );
  }

  return (
    <div className="quiz-container">
      {user.role === 'teacher' ? (
        <>
          <div style={{ padding: '8px 16px', background: 'var(--primary-color)', color: '#03131f', display: 'inline-block', marginBottom: '1rem', borderRadius: '999px', fontWeight: 700 }}>
            Teacher View
          </div>
          {content}
        </>
      ) : content}
    </div>
  );
};

export default QuizPage;
