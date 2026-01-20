import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { chatApi } from '../api/client';
import Avatar from '../components/Avatar';
import MessageBubble from '../components/MessageBubble';
import ResponseButtons from '../components/ResponseButtons';
import ExplanationParts from '../components/ExplanationParts';
import './InteractiveChat.css';
import type { Message, ResponseButton, ExplanationPart } from '../types/chat';

const InteractiveChat = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [currentButtons, setCurrentButtons] = useState<ResponseButton[]>([]);
  const [explanationParts, setExplanationParts] = useState<ExplanationPart[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Welcome message
  useEffect(() => {
    const welcomeMessage: Message = {
      id: 'welcome',
      role: 'ai',
      content: `Hi ${user?.name}! 👋 I'm your AI Science Tutor. I'm here to help you learn science in a way that works best for you. Feel free to ask me anything, and I'll explain it step by step. If you don't understand something, just let me know!`,
      timestamp: new Date(),
      emotion: 'happy',
    };

    setMessages([welcomeMessage]);

    // Set initial buttons
    setCurrentButtons([
      {
        id: 'start',
        label: 'Ask a Question',
        action: 'continue',
        emoji: '❓',
      },
      {
        id: 'break',
        label: 'Take a Break',
        action: 'break',
        emoji: '⏸️',
      },
    ]);
  }, [user?.name]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleButtonClick = async (button: ResponseButton) => {
    if (button.action === 'break') {
      setIsPaused(true);
      const breakMessage: Message = {
        id: Date.now().toString(),
        role: 'ai',
        content: 'Great! Take your time. I\'ll be here whenever you\'re ready to continue. Remember, learning is a journey, not a race! 🌟',
        timestamp: new Date(),
        emotion: 'happy',
      };
      setMessages(prev => [...prev, breakMessage]);
      setCurrentButtons([
        {
          id: 'resume',
          label: 'Resume Learning',
          action: 'continue',
          emoji: '▶️',
        },
        {
          id: 'stop',
          label: 'Stop for Today',
          action: 'stop',
          emoji: '⏹️',
        },
      ]);
      return;
    }

    if (button.action === 'stop') {
      navigate('/dashboard');
      return;
    }

    if (button.action === 'continue' && isPaused) {
      setIsPaused(false);
      const resumeMessage: Message = {
        id: Date.now().toString(),
        role: 'ai',
        content: 'Welcome back! Ready to continue learning? What would you like to explore?',
        timestamp: new Date(),
        emotion: 'happy',
      };
      setMessages(prev => [...prev, resumeMessage]);
      setCurrentButtons([
        {
          id: 'ask',
          label: 'Ask a Question',
          action: 'continue',
          emoji: '❓',
        },
        {
          id: 'break2',
          label: 'Take a Break',
          action: 'break',
          emoji: '⏸️',
        },
      ]);
      return;
    }

    // For other actions, send to backend
    setIsLoading(true);
    try {
      const response = await chatApi.sendMessage({
        session_id: sessionId || undefined,
        content: button.label,
        input_type: 'BUTTON',
      });

      if (response.session_id && !sessionId) {
        setSessionId(response.session_id);
      }

      // Add AI response
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: response.message || 'Let me help you with that!',
        timestamp: new Date(),
        emotion: 'neutral',
      };
      setMessages(prev => [...prev, aiMessage]);

      // Update buttons
      if (response.suggested_responses && response.suggested_responses.length > 0) {
        const newButtons: ResponseButton[] = response.suggested_responses.map((label: string, idx: number) => ({
          id: `btn-${idx}`,
          label,
          action: 'continue',
        }));
        setCurrentButtons(newButtons);
      } else {
        setCurrentButtons([
          {
            id: 'confused',
            label: 'I\'m Confused',
            action: 'confused',
            emoji: '😕',
          },
          {
            id: 'understood',
            label: 'I Understand',
            action: 'understood',
            emoji: '👍',
          },
          {
            id: 'more',
            label: 'Tell Me More',
            action: 'detail',
            emoji: '🔍',
          },
        ]);
      }
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePartClick = async (part: ExplanationPart) => {
    setIsLoading(true);
    try {
      const response = await chatApi.sendMessage({
        session_id: sessionId || undefined,
        content: `Please explain this part in more detail: ${part.title}`,
        input_type: 'TEXT',
      });

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        content: response.message || 'Let me explain that part more clearly...',
        timestamp: new Date(),
        emotion: 'neutral',
      };
      setMessages(prev => [...prev, aiMessage]);
      setExplanationParts([]);

      setCurrentButtons([
        {
          id: 'understood',
          label: 'Got It!',
          action: 'understood',
          emoji: '👍',
        },
        {
          id: 'still-confused',
          label: 'Still Confused',
          action: 'confused',
          emoji: '😕',
        },
      ]);
    } catch (err) {
      console.error('Error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="interactive-chat-container">
      {/* Header */}
      <header className="chat-header">
        <button className="back-button" onClick={() => navigate('/dashboard')}>
          ← Back
        </button>
        <div className="header-title">
          <h1>🎓 Interactive Learning</h1>
          <p>Learn at your own pace</p>
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
              onPartClick={handlePartClick}
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

export default InteractiveChat;
