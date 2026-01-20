import { motion, AnimatePresence } from 'framer-motion';
import './AIAvatarPanel.css';

interface AIAvatarPanelProps {
  message: string;
  isLoading: boolean;
  avatar?: string;
}

export const AIAvatarPanel = ({ message, isLoading, avatar = '🤖' }: AIAvatarPanelProps) => {
  return (
    <div className="ai-avatar-panel">
      {/* Avatar */}
      <div className="avatar-container">
        <div className="avatar-circle ai-avatar">
          {avatar}
        </div>
        <div className="avatar-label">AI Tutor</div>
      </div>

      {/* Message Bubble */}
      <div className="message-area">
        <AnimatePresence mode="wait">
          {isLoading ? (
            <motion.div
              key="loading"
              className="loading-state"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="spinner">
                <div className="dot"></div>
                <div className="dot"></div>
                <div className="dot"></div>
              </div>
              <p>Thinking...</p>
            </motion.div>
          ) : message ? (
            <motion.div
              key={message}
              className="message-bubble ai-bubble"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
            >
              <div className="message-content">
                {message}
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
              <p>Select a section or ask a question to get started</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default AIAvatarPanel;
