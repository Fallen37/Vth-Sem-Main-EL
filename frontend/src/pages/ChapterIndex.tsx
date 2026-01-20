import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { chatApi, contentApi } from '../api/client';
import './ChapterIndex.css';

const ChapterIndex = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [chapters, setChapters] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [sessionMap, setSessionMap] = useState<Record<string, string>>({});
  const [creatingSession, setCreatingSession] = useState<string | null>(null);

  useEffect(() => {
    console.log('ChapterIndex mounted, user:', user?.id);
    loadChapters();
    loadSessionMap();
  }, [user?.grade, user?.id]);

  const loadSessionMap = () => {
    try {
      const stored = localStorage.getItem(`sessionMap_${user?.id}`);
      if (stored) {
        setSessionMap(JSON.parse(stored));
      }
    } catch (err) {
      console.error('Failed to load session map:', err);
    }
  };

  const loadChapters = async () => {
    try {
      setLoading(true);
      const response = await contentApi.getChaptersByGrade(user?.grade || 6);
      const chapterNames = response.chapters.map((ch: any) => ch.chapter);
      setChapters(chapterNames);
    } catch (err) {
      console.error('Failed to load chapters:', err);
      setLoading(false);
    } finally {
      setLoading(false);
    }
  };

  const handleChapterSelect = async (chapter: string) => {
    const existingSessionId = sessionMap[chapter];

    if (existingSessionId) {
      navigate(`/chat?chapter=${encodeURIComponent(chapter)}&session=${existingSessionId}`);
    } else {
      setCreatingSession(chapter);
      try {
        const response = await chatApi.createSession();
        const newSessionId = response.session_id;

        const updatedMap = {
          ...sessionMap,
          [chapter]: newSessionId,
        };
        setSessionMap(updatedMap);
        localStorage.setItem(`sessionMap_${user?.id}`, JSON.stringify(updatedMap));

        navigate(`/chat?chapter=${encodeURIComponent(chapter)}&session=${newSessionId}`);
      } catch (err) {
        console.error('Failed to create session:', err);
        setCreatingSession(null);
      }
    }
  };

  if (loading) {
    return (
      <div className="chapter-index-container">
        <div className="loading">Loading chapters...</div>
      </div>
    );
  }

  return (
    <div className="chapter-index-container">
      <header className="chapter-header">
        <button className="back-button" onClick={() => navigate('/dashboard')}>
          ← Back
        </button>
        <div className="header-title">
          <h1>📚 Grade {user?.grade} Chapters</h1>
          <p>Select a chapter to start learning</p>
        </div>
        <button className="settings-button" onClick={() => navigate('/settings')}>
          ⚙️
        </button>
      </header>

      <div className="chapters-list">
        {chapters.map((chapter, idx) => (
          <button
            key={idx}
            className="chapter-button"
            onClick={() => handleChapterSelect(chapter)}
            disabled={creatingSession === chapter}
          >
            <span className="chapter-number">{idx + 1}</span>
            <span className="chapter-name">{chapter}</span>
            <span className="chapter-icon">
              {sessionMap[chapter] ? '✓' : '→'}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default ChapterIndex;
