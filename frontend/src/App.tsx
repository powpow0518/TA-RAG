import React, { createContext, useContext, useEffect, useState } from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes, Link, useLocation } from 'react-router-dom';
import { Moon, Sun } from 'lucide-react';
import axios from 'axios';

import { AuthProvider, useAuth } from './context/AuthContext';
import ChatPage from './pages/ChatPage';
import LoginPage from './pages/LoginPage';
import QuizPage from './pages/QuizPage';
import RegisterPage from './pages/RegisterPage';

interface Course {
  course_id: string;
  course_name: string;
}

interface CourseContextType {
  courses: Course[];
  currentCourse: Course | null;
  setCurrentCourse: (course: Course) => void;
}

type ThemeMode = 'dark' | 'light';

const CourseContext = createContext<CourseContextType | undefined>(undefined);

export const useCourse = () => {
  const context = useContext(CourseContext);
  if (!context) throw new Error('useCourse must be used within CourseProvider');
  return context;
};

const PrivateRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div>Loading...</div>;
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

const Navigation: React.FC<{ theme: ThemeMode; toggleTheme: () => void }> = ({ theme, toggleTheme }) => {
  const { user, logout, isAuthenticated, loading } = useAuth();
  const { currentCourse, courses, setCurrentCourse } = useCourse();
  const location = useLocation();

  if (loading || !isAuthenticated || location.pathname === '/login' || location.pathname === '/register') {
    return null;
  }

  return (
    <nav className="nav-shell">
      <Link to="/" className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}>Chat</Link>
      <Link to="/quiz" className={`nav-link ${location.pathname === '/quiz' ? 'active' : ''}`}>Quiz</Link>

      <div className="course-picker">
        <span className="muted">Course</span>
        <select
          value={currentCourse?.course_id || ''}
          onChange={(e) => {
            const selected = courses.find((course) => course.course_id === e.target.value);
            if (selected) setCurrentCourse(selected);
          }}
        >
          {courses.map((course) => (
            <option key={course.course_id} value={course.course_id}>
              {course.course_id} - {course.course_name}
            </option>
          ))}
        </select>
      </div>

      <div className="nav-spacer" />
      <button type="button" className="theme-button" onClick={toggleTheme}>
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      </button>
      <div className="nav-chip">{user?.username}</div>
      <button type="button" onClick={logout}>Logout</button>
    </nav>
  );
};

const AppContent: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [currentCourse, setCurrentCourse] = useState<Course | null>(null);
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('theme-mode');
    return saved === 'light' ? 'light' : 'dark';
  });

  useEffect(() => {
    document.body.classList.remove('theme-dark', 'theme-light');
    document.body.classList.add(theme === 'dark' ? 'theme-dark' : 'theme-light');
    localStorage.setItem('theme-mode', theme);
  }, [theme]);

  useEffect(() => {
    if (isAuthenticated) {
      axios.get('/api/v1/courses/').then((res) => {
        setCourses(res.data);
        if (res.data.length > 0) setCurrentCourse(res.data[0]);
      }).catch((err) => console.error('Failed to fetch courses', err));
    }
  }, [isAuthenticated]);

  return (
    <CourseContext.Provider value={{ courses, currentCourse, setCurrentCourse }}>
      <Router>
        <div className="app-container">
          <div className="app-shell">
            <Navigation
              theme={theme}
              toggleTheme={() => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))}
            />
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route
                path="/"
                element={(
                  <PrivateRoute>
                    <ChatPage />
                  </PrivateRoute>
                )}
              />
              <Route
                path="/quiz"
                element={(
                  <PrivateRoute>
                    <QuizPage />
                  </PrivateRoute>
                )}
              />
            </Routes>
          </div>
        </div>
      </Router>
    </CourseContext.Provider>
  );
};

const App: React.FC = () => (
  <AuthProvider>
    <AppContent />
  </AuthProvider>
);

export default App;
