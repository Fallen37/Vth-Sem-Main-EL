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
      content: `Hi ${user?.name}! 👋 I'm your Science Tutor. Ask me anything about science - physics, chemistry, biology, or any topic you're curious about!`,
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
        content: response.message || "I'm here to help! Could you tell me more about what you'd like to learn?",
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      
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

  return (
    <div className="chat-container">
      <header className="chat-header">
        <button className="back-button" onClick={() => navigate('/dashboard')}>
          ← Back
        </button>
        <div className="chat-title">
          <h1>💬 Chat with Tutor</h1>
        </div>
        <button className="calm-mode-btn" onClick={() => navigate('/calm')}>
          🧘
        </button>
      </header>

      <div className="chat-content">
        <div className="messages-list">
          {messages.map(message => (
            <div key={message.id} className={`message ${message.role}`}>
              <div className="message-bubble">
                <div className="message-label">
                  {message.role === 'assistant' ? 'Tutor' : 'You'}
                </div>
                <div className="message-content">
                  <p>{message.content}</p>
                </div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message assistant">
              <div className="message-bubble">
                <div className="message-label">Tutor</div>
                <div className="message-content typing">
                  <span className="typing-dot"></span>
                  <span className="typing-dot"></span>
                  <span className="typing-dot"></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

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
      </div>
    </div>
  );
};

export default Chat;
