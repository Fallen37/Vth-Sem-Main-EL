import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './UserAvatarPanel.css';

interface UserAvatarPanelProps {
  userMessage: string;
  onSendMessage: (message: string) => Promise<void>;
  onFeedback: (liked: boolean) => Promise<void>;
  isLoading: boolean;
  avatar?: string;
  userName?: string;
}

export const UserAvatarPanel = ({
  userMessage,
  onSendMessage,
  onFeedback,
  isLoading,
  avatar = '👤',
  userName = 'You',
}: UserAvatarPanelProps) => {
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    setIsSending(true);
    try {
      await onSendMessage(inputValue);
      setInputValue('');
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="user-avatar-panel">
      {/* Avatar */}
      <div className="avatar-container">
        <div className="avatar-circle user-avatar">
          {avatar}
        </div>
        <div className="avatar-label">{userName}</div>
      </div>

      {/* Message Display */}
      <div className="message-area">
        <AnimatePresence mode="wait">
          {userMessage ? (
            <motion.div
              key={userMessage}
              className="message-bubble user-bubble"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              <div className="message-content">
                {userMessage}
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              className="empty-state"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <p>Your message will appear here</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Feedback Buttons */}
      <div className="feedback-buttons">
        <motion.button
          className="feedback-btn understood-btn"
          onClick={() => onFeedback(true)}
          disabled={isLoading || isSending || !userMessage}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          title="Mark as understood"
        >
          <span className="btn-emoji">👍</span>
          <span className="btn-text">Got it</span>
        </motion.button>

        <motion.button
          className="feedback-btn confused-btn"
          onClick={() => onFeedback(false)}
          disabled={isLoading || isSending || !userMessage}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          title="Mark as unclear"
        >
          <span className="btn-emoji">🤔</span>
          <span className="btn-text">Unclear</span>
        </motion.button>
      </div>

      {/* Input Area */}
      <div className="input-area">
        <textarea
          className="input-field"
          placeholder="Ask a question or request clarification..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={isLoading || isSending}
          rows={3}
        />
        <motion.button
          className="send-btn"
          onClick={handleSend}
          disabled={!inputValue.trim() || isLoading || isSending}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {isSending ? '⏳' : '📤'}
          <span>{isSending ? 'Sending...' : 'Send'}</span>
        </motion.button>
      </div>
    </div>
  );
};

export default UserAvatarPanel;
