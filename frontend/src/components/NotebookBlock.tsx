import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import './NotebookBlock.css';

interface NotebookBlockProps {
  blockId: string;
  topicRef: string;
  content: string;
  onAskAI: (blockId: string, topicRef: string, query?: string) => Promise<string>;
  onUpdate: (blockId: string, newContent: string) => void;
  isUpdating?: boolean;
}

export const NotebookBlock = ({
  blockId,
  topicRef,
  content,
  onAskAI,
  onUpdate,
  isUpdating = false,
}: NotebookBlockProps) => {
  const [isHovered, setIsHovered] = useState(false);
  const [isActive, setIsActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [showQueryInput, setShowQueryInput] = useState(false);
  const [query, setQuery] = useState('');
  const blockRef = useRef<HTMLDivElement>(null);

  const handleAskAI = async (customQuery?: string) => {
    setIsLoading(true);
    try {
      const result = await onAskAI(blockId, topicRef, customQuery || query);
      onUpdate(blockId, result);
      setShowQueryInput(false);
      setQuery('');
    } catch (error) {
      console.error('Error asking AI:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickAction = async (action: string) => {
    const queries: Record<string, string> = {
      simplify: 'Explain this in simpler terms',
      expand: 'Expand this with more details',
      points: 'Convert this to bullet points',
      summary: 'Summarize this in one sentence',
    };
    
    await handleAskAI(queries[action] || action);
  };

  const handleBlockClick = () => {
    setIsActive(!isActive);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && isActive) {
      setShowQueryInput(true);
    } else if (e.key === 'Escape') {
      setIsActive(false);
      setShowQueryInput(false);
    }
  };

  return (
    <motion.div
      ref={blockRef}
      className={`notebook-block ${isActive ? 'active' : ''} ${isHovered ? 'hovered' : ''}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleBlockClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-pressed={isActive}
      aria-label={`Block: ${content.substring(0, 50)}...`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
      whileHover={{ y: -2 }}
    >
      {/* Block Card Container */}
      <motion.div
        className="block-card"
        animate={{
          boxShadow: isActive
            ? '0 8px 24px rgba(102, 126, 234, 0.25)'
            : isHovered
            ? '0 4px 12px rgba(102, 126, 234, 0.15)'
            : '0 2px 4px rgba(0, 0, 0, 0.05)',
        }}
        transition={{ duration: 0.2 }}
      >
        {/* Content */}
        <AnimatePresence mode="wait">
          {isUpdating ? (
            <motion.div
              key="updating"
              className="updating-state"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="spinner-small">
                <div className="dot"></div>
                <div className="dot"></div>
                <div className="dot"></div>
              </div>
              <p>Updating...</p>
            </motion.div>
          ) : (
            <motion.div
              key={content}
              className="block-content"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <ReactMarkdown>{content}</ReactMarkdown>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Expand/Collapse Indicator */}
        {isActive && (
          <motion.div
            className="expand-indicator"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            ▼
          </motion.div>
        )}
      </motion.div>

      {/* Floating Toolbar */}
      <AnimatePresence>
        {isActive && !isUpdating && (
          <motion.div
            className="floating-toolbar"
            initial={{ opacity: 0, y: -20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.9 }}
            transition={{ duration: 0.2, type: 'spring', stiffness: 300 }}
          >
            {!showQueryInput ? (
              <>
                <motion.button
                  className="toolbar-btn quick-action-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleQuickAction('simplify');
                  }}
                  disabled={isLoading}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  title="Simplify this section (Ctrl+1)"
                >
                  ✨
                </motion.button>
                <motion.button
                  className="toolbar-btn quick-action-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleQuickAction('points');
                  }}
                  disabled={isLoading}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  title="Convert to bullet points (Ctrl+2)"
                >
                  📝
                </motion.button>
                <motion.button
                  className="toolbar-btn quick-action-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleQuickAction('expand');
                  }}
                  disabled={isLoading}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  title="Expand with more details (Ctrl+3)"
                >
                  📖
                </motion.button>
                <motion.button
                  className="toolbar-btn ask-ai-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowQueryInput(true);
                  }}
                  disabled={isLoading}
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  title="Ask AI a custom question (Enter)"
                >
                  💡
                </motion.button>
              </>
            ) : (
              <motion.div
                className="query-input-container"
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                onClick={(e) => e.stopPropagation()}
              >
                <input
                  type="text"
                  className="query-input"
                  placeholder="Ask AI..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && query.trim()) {
                      handleAskAI();
                    }
                  }}
                  autoFocus
                />
                <motion.button
                  className="send-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAskAI();
                  }}
                  disabled={!query.trim() || isLoading}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {isLoading ? '⏳' : '→'}
                </motion.button>
                <motion.button
                  className="cancel-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowQueryInput(false);
                    setQuery('');
                  }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  ✕
                </motion.button>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default NotebookBlock;
