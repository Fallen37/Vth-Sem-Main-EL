import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useLearning } from '../context/LearningContext';
import { chatApi, responsesApi } from '../api/client';
import ExplanationCard from '../components/ExplanationCard';
import LearningNotebook from '../components/LearningNotebook';
import './InteractiveLearnPage.css';

type ViewMode = 'learning' | 'notebook';

export const InteractiveLearnPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { currentCard, setCurrentCard, isLoading, setIsLoading } = useLearning();
  
  const chapter = searchParams.get('chapter');
  const sessionId = searchParams.get('session');
  const [viewMode, setViewMode] = useState<ViewMode>('learning');

  useEffect(() => {
    if (!chapter || !sessionId) {
      navigate('/chapters');
      return;
    }

    initializeLesson();
  }, [chapter, sessionId]);

  const initializeLesson = async () => {
    setIsLoading(true);
    try {
      // Get initial explanation
      const response = await chatApi.sendMessage({
        session_id: sessionId || undefined,
        content: `Please explain the chapter "${chapter}" in a way suitable for a Grade ${user?.grade} student. Start with the basics and build up. Use examples from the textbook if possible.`,
        input_type: 'TEXT',
      });

      // Create card
      setCurrentCard({
        id: `card_${Date.now()}`,
        topic: chapter || 'Learning',
        explanation: response.message,
        liked: undefined,
        iterationLevel: 1,
        createdAt: new Date().toISOString(),
      });
    } catch (error) {
      console.error('Error initializing lesson:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFeedback = async (cardId: string, liked: boolean) => {
    try {
      await responsesApi.updateFeedback({
        response_id: cardId,
        liked,
        feedback_text: liked ? 'Student understood' : 'Student needs clarification',
      });
    } catch (error) {
      console.error('Error sending feedback:', error);
    }
  };

  return (
    <div className="interactive-learn-page">
      {/* Header */}
      <header className="learn-header">
        <div className="header-left">
          <button className="back-btn" onClick={() => navigate('/chapters')}>
            ← Chapters
          </button>
          <h1 className="page-title">📚 {chapter}</h1>
        </div>
        <div className="header-right">
          <button
            className={`settings-btn ${viewMode === 'learning' ? 'active' : ''}`}
            onClick={() => setViewMode('learning')}
            title="Learning Mode"
          >
            🎓 Learn
          </button>
          <button
            className={`settings-btn ${viewMode === 'notebook' ? 'active' : ''}`}
            onClick={() => setViewMode('notebook')}
            title="Notebook View"
          >
            📖 Notebook
          </button>
          <button className="settings-btn" onClick={() => navigate('/dashboard')} title="Dashboard">
            🏠
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="learn-main">
        {viewMode === 'learning' ? (
          <div className="learning-view">
            {isLoading && !currentCard ? (
              <div className="loading-state">
                <div className="loading-spinner">⏳</div>
                <p>Loading explanation...</p>
              </div>
            ) : currentCard ? (
              <ExplanationCard
                id={currentCard.id}
                topic={currentCard.topic}
                explanation={currentCard.explanation}
                metaText={currentCard.metaText}
                liked={currentCard.liked}
                iterationLevel={currentCard.iterationLevel}
                onFeedback={handleFeedback}
              />
            ) : null}

            {/* Navigation Buttons */}
            <div className="navigation-section">
              <button className="nav-btn secondary" onClick={() => navigate('/chapters')}>
                ← Back to Chapters
              </button>
              <button className="nav-btn primary" onClick={() => navigate('/dashboard')}>
                Go to Dashboard →
              </button>
            </div>
          </div>
        ) : (
          <div className="notebook-view">
            <LearningNotebook />
          </div>
        )}
      </main>
    </div>
  );
};

export default InteractiveLearnPage;
