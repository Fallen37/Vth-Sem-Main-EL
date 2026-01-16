import { useState, useEffect, useRef } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { chatApi } from '../api/client';
import './Chat.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

type AvatarState = 'idle' | 'listening' | 'thinking' | 'explaining';

const Chat = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [tutorState, setTutorState] = useState<AvatarState>('idle');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Add welcome message
    setMessages([{
      id: 'welcome',
      role: 'assistant',
      content: `Hi ${user?.name}! 👋 I'm Science Buddy, your AI tutor. Ask me anything about science - physics, chemistry, biology, or any topic you're curious about!`,
      timestamp: new Date(),
    }]);
  }, [user?.name]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setTutorState('thinking');

    try {
      const response = await chatApi.sendMessage({
        session_id: sessionId || undefined,
        content: userMessage.content,
        input_type: 'TEXT',
      });

      if (response.session_id && !sessionId) {
        setSessionId(response.session_id);
      }

      setTutorState('explaining');

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content || response.message || "I'm here to help! Could you tell me more about what you'd like to learn?",
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      // Return to idle after a delay
      setTimeout(() => setTutorState('idle'), 2000);
    } catch (err) {
      console.error('Failed to send message:', err);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "Oops! I had trouble processing that. Let me try again - could you rephrase your question?",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
      setTutorState('idle');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as FormEvent);
    }
  };

  const handleInputFocus = () => {
    if (!isLoading) {
      setTutorState('listening');
    }
  };

  const handleInputBlur = () => {
    if (!isLoading && tutorState === 'listening') {
      setTutorState('idle');
    }
  };

  const getAvatarAnimation = () => {
    switch (tutorState) {
      case 'listening': return 'avatar-listening';
      case 'thinking': return 'avatar-thinking';
      case 'explaining': return 'avatar-explaining';
      default: return 'avatar-idle';
    }
  };

  const getStateLabel = () => {
    switch (tutorState) {
      case 'listening': return 'Listening...';
      case 'thinking': return 'Thinking...';
      case 'explaining': return 'Explaining...';
      default: return 'Ready to help!';
    }
  };

  return (
    <div className="chat-container">
      <header className="chat-header">
        <button className="back-button" onClick={() => navigate('/dashboard')}>
          ← Back
        </button>
        <div className="chat-title">
          <h1>💬 Science Buddy</h1>
        </div>
        <button className="calm-mode-btn" onClick={() => navigate('/calm')}>
          🧘
        </button>
      </header>

      <div className="chat-content">
        {/* Avatar Panel */}
        <aside className="avatar-panel">
          <div className={`tutor-avatar-large ${getAvatarAnimation()}`}>
            <div className="avatar-face">
              <span className="avatar-emoji-large">🤖</span>
            </div>
            <div className="avatar-state-indicator">
              <span className={`state-dot ${tutorState}`}></span>
              <span className="state-label">{getStateLabel()}</span>
            </div>
          </div>
          
          <div className="student-avatar-small">
            <span className="student-emoji">👤</span>
            <span className="student-name">{user?.name}</span>
          </div>

          <div className="quick-topics">
            <h3>Quick Topics</h3>
            <button onClick={() => setInput("What is photosynthesis?")}>🌱 Photosynthesis</button>
            <button onClick={() => setInput("Explain Newton's laws of motion")}>⚡ Newton's Laws</button>
            <button onClick={() => setInput("What are atoms made of?")}>⚛️ Atoms</button>
            <button onClick={() => setInput("How does the heart work?")}>❤️ Heart</button>
          </div>
        </aside>

        {/* Messages Area */}
        <main className="messages-area">
          <div className="messages-list">
            {messages.map(message => (
              <div key={message.id} className={`message ${message.role}`}>
                <div className="message-avatar">
                  {message.role === 'assistant' ? '🤖' : '👤'}
                </div>
                <div className="message-content">
                  <p>{message.content}</p>
                  <span className="message-time">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="message assistant">
                <div className="message-avatar">🤖</div>
                <div className="message-content typing">
                  <span className="typing-dot"></span>
                  <span className="typing-dot"></span>
                  <span className="typing-dot"></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <form className="input-area" onSubmit={handleSubmit}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={handleInputFocus}
              onBlur={handleInputBlur}
              placeholder="Ask me anything about science..."
              rows={1}
              disabled={isLoading}
            />
            <button type="submit" disabled={!input.trim() || isLoading}>
              {isLoading ? '⏳' : '📤'}
            </button>
          </form>
        </main>
      </div>
    </div>
  );
};

export default Chat;
