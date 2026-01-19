import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { progressApi, contentApi } from '../api/client';
import { UserRole } from '../types';
import './Dashboard.css';

interface ProgressSummary {
  topics_covered: number;
  total_topics: number;
  current_streak: number;
  recent_achievements: Achievement[];
  strength_areas: Topic[];
  growth_areas: Topic[];
}

interface Achievement {
  id: string;
  achievement_type: string;
  title: string;
  description: string;
  earned_at: string;
}

interface Topic {
  topic_id: string;
  topic_name: string;
  grade: number;
}

interface ContentSummary {
  total_documents: number;
  by_subject: Record<string, number>;
}

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [progress, setProgress] = useState<ProgressSummary | null>(null);
  const [content, setContent] = useState<ContentSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [progressData, contentData] = await Promise.all([
          progressApi.getSummary().catch(() => null),
          contentApi.getSummary().catch(() => null),
        ]);
        setProgress(progressData);
        setContent(contentData);
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const progressPercent = progress 
    ? Math.round((progress.topics_covered / Math.max(progress.total_topics, 1)) * 100)
    : 0;

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="logo">🌟 Science Tutor</div>
        <div className="user-menu">
          <span className="user-name">Hi, {user?.name}!</span>
          <button onClick={handleLogout} className="logout-button">Sign Out</button>
        </div>
      </header>

      <main className="dashboard-main">
        <section className="welcome-section">
          <h1>Welcome back, {user?.name}! 👋</h1>
          <p>Ready to explore science today?</p>
        </section>

        {/* Avatar Chat Card - Main CTA */}
        <section className="avatar-section">
          <div className="avatar-card" onClick={() => navigate('/chat')}>
            <div className="avatar-container">
              <div className="tutor-avatar">
                <span className="avatar-emoji">🤖</span>
                <div className="avatar-pulse"></div>
              </div>
            </div>
            <div className="avatar-info">
              <h2>Science Buddy</h2>
              <p>Your AI tutor is ready to help!</p>
              <button className="start-chat-btn">Start Learning 💬</button>
            </div>
          </div>
        </section>

        {/* Progress Overview */}
        <section className="progress-section">
          <h2>📊 Your Progress</h2>
          {loading ? (
            <div className="loading-card">Loading...</div>
          ) : (
            <div className="progress-grid">
              <div className="progress-card main-progress">
                <div className="progress-ring">
                  <svg viewBox="0 0 100 100">
                    <circle className="progress-bg" cx="50" cy="50" r="45" />
                    <circle 
                      className="progress-fill" 
                      cx="50" cy="50" r="45"
                      style={{ strokeDashoffset: 283 - (283 * progressPercent / 100) }}
                    />
                  </svg>
                  <span className="progress-text">{progressPercent}%</span>
                </div>
                <div className="progress-details">
                  <h3>Topics Covered</h3>
                  <p>{progress?.topics_covered || 0} of {progress?.total_topics || 0}</p>
                </div>
              </div>

              <div className="progress-card streak-card">
                <span className="streak-icon">🔥</span>
                <div className="streak-info">
                  <h3>{progress?.current_streak || 0} Day Streak</h3>
                  <p>Keep it going!</p>
                </div>
              </div>

              {progress?.strength_areas && progress.strength_areas.length > 0 && (
                <div className="progress-card strengths-card">
                  <h3>💪 Your Strengths</h3>
                  <ul>
                    {progress.strength_areas.slice(0, 3).map(topic => (
                      <li key={topic.topic_id}>{topic.topic_name}</li>
                    ))}
                  </ul>
                </div>
              )}

              {progress?.growth_areas && progress.growth_areas.length > 0 && (
                <div className="progress-card growth-card">
                  <h3>🌱 Areas to Grow</h3>
                  <ul>
                    {progress.growth_areas.slice(0, 3).map(topic => (
                      <li key={topic.topic_id}>{topic.topic_name}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Recent Achievements */}
        {progress?.recent_achievements && progress.recent_achievements.length > 0 && (
          <section className="achievements-section">
            <h2>🏆 Recent Achievements</h2>
            <div className="achievements-list">
              {progress.recent_achievements.slice(0, 4).map(achievement => (
                <div key={achievement.id} className="achievement-badge">
                  <span className="badge-icon">⭐</span>
                  <div className="badge-info">
                    <h4>{achievement.title}</h4>
                    <p>{achievement.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Learning Materials */}
        <section className="materials-section">
          <h2>📚 Learning Materials</h2>
          <div className="materials-grid">
            {content?.by_subject && Object.entries(content.by_subject).length > 0 ? (
              Object.entries(content.by_subject).map(([subject, count]) => (
                <div key={subject} className="material-card" onClick={() => navigate(`/materials?subject=${subject}`)}>
                  <span className="material-icon">
                    {subject.toLowerCase().includes('physics') ? '⚡' :
                     subject.toLowerCase().includes('chemistry') ? '🧪' :
                     subject.toLowerCase().includes('biology') ? '🧬' : '📖'}
                  </span>
                  <h3>{subject}</h3>
                  <p>{count} documents</p>
                </div>
              ))
            ) : (
              <>
                <div className="material-card" onClick={() => navigate('/materials?subject=Physics')}>
                  <span className="material-icon">⚡</span>
                  <h3>Physics</h3>
                  <p>Explore forces & motion</p>
                </div>
                <div className="material-card" onClick={() => navigate('/materials?subject=Chemistry')}>
                  <span className="material-icon">🧪</span>
                  <h3>Chemistry</h3>
                  <p>Discover elements & reactions</p>
                </div>
                <div className="material-card" onClick={() => navigate('/materials?subject=Biology')}>
                  <span className="material-icon">🧬</span>
                  <h3>Biology</h3>
                  <p>Learn about life</p>
                </div>
              </>
            )}
          </div>
        </section>

        {/* Quick Actions */}
        <section className="quick-actions">
          <div className="action-card" onClick={() => navigate('/progress')}>
            <span className="action-icon">📈</span>
            <h3>Detailed Progress</h3>
            <p>View full learning history</p>
          </div>

          <div className="action-card" onClick={() => navigate('/settings')}>
            <span className="action-icon">⚙️</span>
            <h3>Settings</h3>
            <p>Customize your experience</p>
          </div>

          {user?.role === UserRole.GUARDIAN && (
            <div className="action-card" onClick={() => navigate('/guardian')}>
              <span className="action-icon">👨‍👩‍👧</span>
              <h3>Guardian View</h3>
              <p>Monitor student progress</p>
            </div>
          )}
        </section>

        {/* User Info Card */}
        <section className="info-section">
          <div className="info-card">
            <h3>Your Profile</h3>
            <ul>
              <li><strong>Role:</strong> {user?.role}</li>
              {user?.grade && <li><strong>Grade:</strong> {user.grade}</li>}
              {user?.syllabus && <li><strong>Syllabus:</strong> {user.syllabus}</li>}
            </ul>
          </div>
        </section>
      </main>

      <footer className="dashboard-footer">
        <button className="calm-button" onClick={() => navigate('/calm')}>
          🧘 Take a Break
        </button>
      </footer>
    </div>
  );
};

export default Dashboard;
