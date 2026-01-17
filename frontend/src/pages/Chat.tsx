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

interface TextbookSection {
  id: string;
  title: string;
  content: string;
  isHighlighted: boolean;
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
  const [currentTextbook, setCurrentTextbook] = useState<TextbookSection[]>([]);
  const [highlightedSections, setHighlightedSections] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textbookRef = useRef<HTMLDivElement>(null);

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

      // Extract relevant sections from response
      const relevantSections = response.sources?.map((s: any) => s.document_id) || [];
      setHighlightedSections(relevantSections);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message || "I'm here to help! Could you tell me more about what you'd like to learn?",
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

  return (
    <div className="chat-container">
      <header className="chat-header">
        <button className="back-button" onClick={() => navigate('/dashboard')}>
          ← Back
        </button>
        <div className="chat-title">
          <h1>📚 Learn with Textbooks</h1>
        </div>
        <button className="calm-mode-btn" onClick={() => navigate('/calm')}>
          🧘
        </button>
      </header>

      <div className="chat-content split-layout">
        {/* Textbook Viewer - Left Side */}
        <div className="textbook-viewer">
          <div className="textbook-header">
            <h2>TEXTBOOK MATERIAL</h2>
          </div>
          <div className="textbook-content" ref={textbookRef}>
            {currentTextbook.length > 0 ? (
              currentTextbook.map(section => (
                <div 
                  key={section.id}
                  className={`textbook-section ${highlightedSections.includes(section.id) ? 'highlighted' : ''}`}
                >
                  <h3>{section.title}</h3>
                  <p>{section.content}</p>
                </div>
              ))
            ) : (
              <div className="textbook-placeholder">
                <p>Select a topic to view textbook material</p>
              </div>
            )}
          </div>
        </div>

        {/* Chat Interface - Right Side */}
        <div className="chat-interface">
          <div className="messages-list">
            {messages.map(message => (
              <div key={message.id} className={`message ${message.role}`}>
                <div className="message-bubble">
                  <div className="message-label">
                    {message.role === 'assistant' ? 'Response from the AI' : 'Doubt from the user'}
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
                  <div className="message-label">Response from the AI</div>
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
        </div>
      </div>
    </div>
  );
};

export default Chat;
