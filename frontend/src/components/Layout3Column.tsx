import { useState, useCallback, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { NotebookEntry } from './NotebookCanvas';
import AIAvatarPanel from './AIAvatarPanel';
import UserAvatarPanel from './UserAvatarPanel';
import NotebookCanvas from './NotebookCanvas';
import { chatApi, responsesApi } from '../api/client';
import './Layout3Column.css';

interface Layout3ColumnProps {
  chapterTitle?: string;
  sessionId?: string;
}

export const Layout3Column = ({
  chapterTitle: propChapterTitle = 'Learning Session',
  sessionId: propSessionId,
}: Layout3ColumnProps) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Get chapter and session from URL params or props
  const chapter = searchParams.get('chapter') || propChapterTitle;
  const sessionId = searchParams.get('session') || propSessionId;

  // AI Panel State
  const [aiMessage, setAiMessage] = useState('');
  const [aiLoading, setAiLoading] = useState(false);

  // User Panel State
  const [userMessage, setUserMessage] = useState('');
  const [userLoading, setUserLoading] = useState(false);

  // Notebook State
  const [notebookEntries, setNotebookEntries] = useState<NotebookEntry[]>([]);
  const [hasLoadedEntries, setHasLoadedEntries] = useState(false);

  const loadNotebookEntries = async () => {
    try {
      if (sessionId) {
        const data = await responsesApi.getSessionResponses(sessionId);
        const entries: NotebookEntry[] = (data.responses || []).map(
          (response: any, index: number) => ({
            blockId: response.id || `block_${index}`,
            topicRef: response.topic || 'general',
            content: response.content_text || response.explanation || '',
            timestamp: response.created_at || new Date().toISOString(),
          })
        );
        setNotebookEntries(entries);
        setHasLoadedEntries(true);
        
        // If we loaded existing entries, show the last AI message
        if (entries.length > 0) {
          setAiMessage(entries[entries.length - 1].content);
        }
      }
    } catch (error) {
      console.error('Error loading notebook entries:', error);
      setHasLoadedEntries(true);
    }
  };

  // Load initial notebook entries
  useEffect(() => {
    loadNotebookEntries();
  }, [sessionId]);

  // Initialize with first subtopic explanation
  useEffect(() => {
    if (sessionId && chapter && hasLoadedEntries && notebookEntries.length === 0 && !aiLoading) {
      initializeWithFirstSubtopic();
    }
  }, [sessionId, chapter, hasLoadedEntries, notebookEntries.length]);

  const initializeWithFirstSubtopic = async () => {
    setAiLoading(true);
    try {
      // Request explanation of the first subtopic
      const response = await chatApi.sendMessage({
        session_id: sessionId,
        content: `Please explain the first subtopic of "${chapter}" in a way suitable for a Grade student. Start with the basics and build up. Use examples from the textbook if possible. Explain only the FIRST subtopic, then stop and wait for confirmation before continuing.`,
        input_type: 'TEXT',
      });

      // Display AI response
      setAiMessage(response.message || '');

      // Add to notebook
      const newEntry: NotebookEntry = {
        blockId: `block_${Date.now()}`,
        topicRef: `${chapter} - Introduction`,
        content: response.message || '',
        timestamp: new Date().toISOString(),
      };

      setNotebookEntries([newEntry]);

      // Store response
      if (sessionId) {
        await responsesApi.storeResponse({
          session_id: sessionId,
          topic: `${chapter} - Introduction`,
          explanation: response.message || '',
          content_text: response.message || '',
        });
      }
    } catch (error) {
      console.error('Error initializing with first subtopic:', error);
      setAiMessage('Sorry, there was an error loading the first subtopic.');
    } finally {
      setAiLoading(false);
    }
  };

  const handleSendMessage = useCallback(
    async (message: string) => {
      if (!message.trim()) return;

      setUserMessage(message);
      setUserLoading(true);
      setAiLoading(true);

      try {
        // Send message to AI
        const response = await chatApi.sendMessage({
          session_id: sessionId,
          content: message,
          input_type: 'TEXT',
        });

        // Display AI response
        setAiMessage(response.message || '');

        // Add to notebook
        const newEntry: NotebookEntry = {
          blockId: `block_${Date.now()}`,
          topicRef: chapter,
          content: response.message || '',
          timestamp: new Date().toISOString(),
        };

        setNotebookEntries((prev) => [...prev, newEntry]);

        // Store response
        if (sessionId) {
          await responsesApi.storeResponse({
            session_id: sessionId,
            topic: chapter,
            explanation: response.message || '',
            content_text: response.message || '',
          });
        }
      } catch (error) {
        console.error('Error sending message:', error);
        setAiMessage('Sorry, there was an error processing your request.');
      } finally {
        setUserLoading(false);
        setAiLoading(false);
      }
    },
    [sessionId, chapter]
  );

  const handleFeedback = useCallback(
    async (liked: boolean) => {
      if (!userMessage) return;

      try {
        // Find the last AI response in notebook
        const lastEntry = notebookEntries[notebookEntries.length - 1];
        if (lastEntry) {
          await responsesApi.updateFeedback({
            response_id: lastEntry.blockId,
            liked,
            feedback_text: liked ? 'Student understood' : 'Student needs clarification',
          });

          if (liked) {
            // User understood - move to next subtopic
            setAiLoading(true);
            const response = await chatApi.sendMessage({
              session_id: sessionId,
              content: `Understood. Move onto the next topic`,
              input_type: 'TEXT',
            });

            // Add new subtopic to notebook
            const newEntry: NotebookEntry = {
              blockId: `block_${Date.now()}`,
              topicRef: `${chapter} - Subtopic ${notebookEntries.length + 1}`,
              content: response.message || '',
              timestamp: new Date().toISOString(),
            };

            setNotebookEntries((prev) => [...prev, newEntry]);
            setAiMessage(response.message || '');

            // Store response
            if (sessionId) {
              await responsesApi.storeResponse({
                session_id: sessionId,
                topic: `${chapter} - Subtopic ${notebookEntries.length + 1}`,
                explanation: response.message || '',
                content_text: response.message || '',
              });
            }
            setAiLoading(false);
          } else {
            // User didn't understand - request simpler explanation
            setAiLoading(true);
            const response = await chatApi.sendMessage({
              session_id: sessionId,
              content: `Re explain the topic in simpler terms`,
              input_type: 'TEXT',
            });

            // Update the last entry with simpler explanation
            setNotebookEntries((prev) => {
              const updated = [...prev];
              if (updated.length > 0) {
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: response.message || '',
                };
              }
              return updated;
            });

            setAiMessage(response.message || '');
            setAiLoading(false);
          }
        }
      } catch (error) {
        console.error('Error handling feedback:', error);
        setAiLoading(false);
      }
    },
    [userMessage, notebookEntries, sessionId, chapter]
  );

  const handleAskAI = useCallback(
    async (_blockId: string, topicRef: string, query?: string): Promise<string> => {
      try {
        // Request clarification for specific block
        const response = await chatApi.sendMessage({
          session_id: sessionId,
          content: `Clarify this section: "${topicRef}". ${query || 'Explain this section'}`,
          input_type: 'TEXT',
        });

        setAiMessage(response.message || '');
        return response.message || '';
      } catch (error) {
        console.error('Error asking AI:', error);
        throw error;
      }
    },
    [sessionId]
  );

  const handleUpdateBlock = useCallback((blockId: string, newContent: string) => {
    setNotebookEntries((prev: NotebookEntry[]) =>
      prev.map((entry: NotebookEntry) =>
        entry.blockId === blockId ? { ...entry, content: newContent } : entry
      )
    );
  }, []);

  return (
    <div className="layout-3column">
      {/* Header */}
      <header className="layout-header">
        <div className="header-left">
          <button
            className="back-btn"
            onClick={() => navigate('/chapters')}
            title="Go back to chapters"
          >
            ← Chapters
          </button>
          <h1 className="page-title">📚 {chapter}</h1>
        </div>
        <div className="header-right">
          <button
            className="nav-btn"
            onClick={() => navigate('/dashboard')}
            title="Go to dashboard"
          >
            🏠 Dashboard
          </button>
        </div>
      </header>

      {/* Main 3-Column Layout */}
      <main className="layout-main">
        {/* Left Column: AI Avatar Panel */}
        <div className="column column-left">
          <AIAvatarPanel
            message={aiMessage}
            isLoading={aiLoading}
            avatar="/ai-avatar-1.png"
          />
        </div>

        {/* Middle Column: Notebook Canvas */}
        <div className="column column-middle">
          <NotebookCanvas
            entries={notebookEntries}
            onAskAI={handleAskAI}
            onUpdate={handleUpdateBlock}
            chapterTitle={chapter}
          />
        </div>

        {/* Right Column: User Avatar Panel */}
        <div className="column column-right">
          <UserAvatarPanel
            userMessage={userMessage}
            onSendMessage={handleSendMessage}
            onFeedback={handleFeedback}
            isLoading={userLoading}
            avatar="/user-avatar-1.png"
            userName="You"
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="layout-footer">
        <div className="footer-info">
          <span className="info-item">
            📖 {notebookEntries.length} section{notebookEntries.length !== 1 ? 's' : ''}
          </span>
          <span className="info-item">
            💬 Session: {sessionId ? sessionId.substring(0, 8) : 'N/A'}
          </span>
        </div>
      </footer>
    </div>
  );
};

export default Layout3Column;
