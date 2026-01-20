import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { chatApi, contentApi } from '../api/client';
import Avatar from '../components/Avatar';
import MessageBubble from '../components/MessageBubble';
import ResponseButtons from '../components/ResponseButtons';
import ExplanationParts from '../components/ExplanationParts';
import './Chat.css';
import type { Message, ResponseButton, ExplanationPart } from '../types/chat';

const Chat = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const chapter = searchParams.get('chapter');
  const sessionIdParam = searchParams.get('session');

  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId] = useState<string | null>(sessionIdParam);
  const [isLoading, setIsLoading] = useState(false);
  const [currentButtons, setCurrentButtons] = useState<ResponseButton[]>([]);
  const [explanationParts] = useState<ExplanationPart[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [topics, setTopics] = useState<string[]>([]);
  const [currentTopicIndex, setCurrentTopicIndex] = useState(0);
  const [isFirstLoad, setIsFirstLoad] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load chapter topics and initialize chat
  useEffect(() => {
    if (!chapter || !sessionId) return;

    const initializeChat = async () => {
      try {
        // Load previous messages if session exists
        const messagesResponse = await chatApi.getSessionMessages(sessionId);
        if (messagesResponse.messages && messagesResponse.messages.length > 0) {
          // Resume existing session
          const loadedMessages: Message[] = messagesResponse.messages.map((msg: any) => ({
            id: msg.id,
            role: msg.role === 'ai' ? 'ai' : 'user',
            content: msg.content,
            timestamp: new Date(msg.timestamp),
            emotion: msg.role === 'ai' ? 'neutral' : undefined,
          }));
          setMessages(loadedMessages);
          setIsFirstLoad(false);
        } else {
          // New session - get chapter topics from backend
          const chapterResponse = await contentApi.getChapterContent(user?.grade || 6, chapter);
          const topicsList = chapterResponse.topics || [];
          setTopics(topicsList);
          setCurrentTopicIndex(0);

          // Request AI to explain first topic immediately
          setIsLoading(true);
          try {
            const response = await chatApi.sendMessage({
              session_id: sessionId || undefined,
              content: `Please explain the chapter "${chapter}" in a way suitable for a Grade ${user?.grade} student. Start with the basics and build up. Use examples from the textbook if possible.`,
              input_type: 'TEXT',
            });

            const aiMessage: Message = {
              id: (Date.now()).toString(),
              role: 'ai',
              content: response.message || `Let me explain ${chapter}...`,
              timestamp: new Date(),
              emotion: 'neutral',
            };
            setMessages([aiMessage]);

            // Set comprehension buttons
            setCurrentButtons([
              {
                id: 'understood',
                label: 'I Understand',
                action: 'understood',
                emoji: '👍',
              },
              {
                id: 'confused',
                label: 'I\'m Confused',
                action: 'confused',
                emoji: '😕',
              },
              {
                id: 'more',
                label: 'Tell Me More',
                action: 'detail',
                emoji: '🔍',
              },
            ]);
          } catch (err) {
            console.error('Error explaining topic:', err);
            const fallbackMessage: Message = {
              id: 'fallback',
              role: 'ai',
              content: `Hi ${user?.name}! 👋 Let's learn about ${chapter}. Ask me anything about this chapter!`,
              timestamp: new Date(),
              emotion: 'happy',
            };
            setMessages([fallbackMessage]);
          } finally {
            setIsLoading(false);
          }

          setIsFirstLoad(false);
        }
      } catch (err) {
        console.error('Failed to initialize chat:', err);
        // Fallback to simple welcome
        const welcomeMessage: Message = {
          id: 'welcome',
          role: 'ai',
          content: `Hi ${user?.name}! 👋 Let's learn about ${chapter}. Ask me anything about this chapter!`,
          timestamp: new Date(),
          emotion: 'happy',
        };
        setMessages([welcomeMessage]);
        setIsFirstLoad(false);
      }
    };

    if (isFirstLoad) {
      initializeChat();
    }
  }, [chapter, sessionId, user?.name, user?.grade, isFirstLoad]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleButtonClick = async (button: ResponseButton) => {
    if (button.action === 'understood') {
      // Move to next section/topic
      const nextIndex = currentTopicIndex + 1;
      
      if (nextIndex < topics.length) {
        // More topics to explain
        setCurrentTopicIndex(nextIndex);

        const nextTopicMessage: Message = {
          id: Date.now().toString(),
          role: 'ai',
          content: `Great! 👍 Now let's learn about the next part...`,
          timestamp: new Date(),
          emotion: 'happy',
        };
        setMessages(prev => [...prev, nextTopicMessage]);

        // Request explanation for next topic
        setIsLoading(true);
        try {
          const response = await chatApi.sendMessage({
            session_id: sessionId || undefined,
            content: `Please explain the next main concept or section from the chapter "${chapter}". Focus on ONE section only. Use examples from the textbook.`,
            input_type: 'TEXT',
          });

          const aiMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'ai',
            content: response.message || `Let me explain the next part...`,
            timestamp: new Date(),
            emotion: 'neutral',
          };
          setMessages(prev => [...prev, aiMessage]);

          // Reset buttons for next section
          setCurrentButtons([
            {
              id: 'understood',
              label: 'I Understand',
              action: 'understood',
              emoji: '👍',
            },
            {
              id: 'confused',
              label: 'I\'m Confused',
              action: 'confused',
              emoji: '😕',
            },
            {
              id: 'more',
              label: 'Tell Me More',
              action: 'detail',
              emoji: '🔍',
            },
          ]);
        } catch (err) {
          console.error('Error:', err);
        } finally {
          setIsLoading(false);
        }
      } else {
        // All topics completed
        const completionMessage: Message = {
          id: Date.now().toString(),
          role: 'ai',
          content: `🎓 Fantastic! You've completed all sections in this chapter! You've learned about:\n\n${topics.map((t, i) => `${i + 1}. ${t}`).join('\n')}\n\nWould you like to review any section, or move to another chapter?`,
          timestamp: new Date(),
          emotion: 'happy',
        };
        setMessages(prev => [...prev, completionMessage]);

        setCurrentButtons([
          {
            id: 'review',
            label: 'Review a Section',
            action: 'continue',
            emoji: '🔄',
          },
          {
            id: 'next-chapter',
            label: 'Next Chapter',
            action: 'continue',
            emoji: '📚',
          },
          {
            id: 'home',
            label: 'Go Home',
            action: 'continue',
            emoji: '🏠',
          },
        ]);
      }
    } else if (button.action === 'confused') {
      // Ask for simpler explanation of current section
      setIsLoading(true);
      try {
        const response = await chatApi.sendMessage({
          session_id: sessionId || undefined,
          content: `I'm confused about this section. Can you explain it in a simpler way? Use easier words and more examples.`,
          input_type: 'TEXT',
        });

        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'ai',
          content: response.message || 'Let me explain this more simply...',
          timestamp: new Date(),
          emotion: 'neutral',
        };
        setMessages(prev => [...prev, aiMessage]);

        setCurrentButtons([
          {
            id: 'understood-now',
            label: 'Got It Now!',
            action: 'understood',
            emoji: '👍',
          },
          {
            id: 'still-confused',
            label: 'Still Confused',
            action: 'confused',
            emoji: '😕',
          },
          {
            id: 'more-help',
            label: 'More Help',
            action: 'detail',
            emoji: '🔍',
          },
        ]);
      } catch (err) {
        console.error('Error:', err);
      } finally {
        setIsLoading(false);
      }
    } else if (button.action === 'detail') {
      // Provide more details on current section
      setIsLoading(true);
      try {
        const response = await chatApi.sendMessage({
          session_id: sessionId || undefined,
          content: `Tell me more about this section. Include more examples and details from the textbook.`,
          input_type: 'TEXT',
        });

        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'ai',
          content: response.message || 'Here are more details...',
          timestamp: new Date(),
          emotion: 'neutral',
        };
        setMessages(prev => [...prev, aiMessage]);

        setCurrentButtons([
          {
            id: 'understood-detail',
            label: 'I Understand',
            action: 'understood',
            emoji: '👍',
          },
          {
            id: 'confused-detail',
            label: 'I\'m Confused',
            action: 'confused',
            emoji: '😕',
          },
        ]);
      } catch (err) {
        console.error('Error:', err);
      } finally {
        setIsLoading(false);
      }
    } else if (button.label === 'Next Chapter') {
      navigate('/chapters');
    } else if (button.label === 'Go Home') {
      navigate('/dashboard');
    } else if (button.label === 'Review a Section') {
      // Show section selection
      const reviewButtons: ResponseButton[] = topics.map((topic, idx) => ({
        id: `review-${idx}`,
        label: topic,
        action: 'continue',
      }));
      setCurrentButtons(reviewButtons);
    }
  };

  if (!chapter || !sessionId) {
    return (
      <div className="chat-container">
        <div style={{ padding: '2rem', textAlign: 'center', color: 'white' }}>
          <p>Loading chapter...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-container">
      {/* Header */}
      <header className="chat-header">
        <button className="back-button" onClick={() => navigate('/chapters')}>
          ← Chapters
        </button>
        <div className="header-title">
          <h1>📖 {chapter}</h1>
          <p>Topic {currentTopicIndex + 1} of {topics.length}</p>
        </div>
        <button className="settings-button" onClick={() => navigate('/settings')}>
          ⚙️
        </button>
      </header>

      {/* Main Content */}
      <div className="chat-main">
        {/* Left Sidebar - AI Tutor */}
        <div className="tutor-section">
          <div className="tutor-avatar-large">
            <Avatar role="ai" size="large" emotion="happy" />
          </div>
          <div className="tutor-info">
            <h2>AI Tutor</h2>
            <p>Here to help you learn</p>
          </div>
        </div>

        {/* Center - Messages */}
        <div className="messages-section">
          <div className="messages-list">
            {messages.map(message => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isLoading && (
              <div className="loading-indicator">
                <div className="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Response Buttons */}
          {currentButtons.length > 0 && !isLoading && (
            <ResponseButtons 
              buttons={currentButtons} 
              onButtonClick={handleButtonClick}
            />
          )}

          {/* Explanation Parts */}
          {explanationParts.length > 0 && !isLoading && (
            <ExplanationParts 
              parts={explanationParts}
              onPartClick={() => {}}
            />
          )}
        </div>

        {/* Right Sidebar - User & Guardian */}
        <div className="users-section">
          <div className="user-card">
            <Avatar role="user" size="large" emotion="neutral" />
            <h3>You</h3>
            <p>Student</p>
          </div>

          <div className="divider"></div>

          <div className="user-card">
            <Avatar role="assistant" size="large" />
            <h3>Guardian</h3>
            <p>Can help anytime</p>
          </div>

          <div className="quick-actions">
            <button className="quick-action-btn" onClick={() => setIsPaused(!isPaused)}>
              {isPaused ? '▶️ Resume' : '⏸️ Pause'}
            </button>
            <button className="quick-action-btn" onClick={() => navigate('/dashboard')}>
              🏠 Home
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;
