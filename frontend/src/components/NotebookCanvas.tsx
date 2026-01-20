import { useState } from 'react';
import { motion } from 'framer-motion';
import NotebookBlock from './NotebookBlock';
import './NotebookCanvas.css';

export interface NotebookEntry {
  blockId: string;
  topicRef: string;
  content: string;
  timestamp: string;
}

interface NotebookCanvasProps {
  entries: NotebookEntry[];
  onAskAI: (blockId: string, topicRef: string, query?: string) => Promise<string>;
  onUpdate: (blockId: string, newContent: string) => void;
  chapterTitle?: string;
}

export const NotebookCanvas = ({
  entries,
  onAskAI,
  onUpdate,
  chapterTitle = 'Learning Notebook',
}: NotebookCanvasProps) => {
  const [updatingBlocks, setUpdatingBlocks] = useState<Set<string>>(new Set());

  const handleAskAI = async (blockId: string, topicRef: string, query?: string): Promise<string> => {
    setUpdatingBlocks((prev) => new Set(prev).add(blockId));
    try {
      const newContent = await onAskAI(blockId, topicRef, query);
      onUpdate(blockId, newContent);
      return newContent;
    } catch (error) {
      console.error('Error updating block:', error);
      return '';
    } finally {
      setUpdatingBlocks((prev) => {
        const next = new Set(prev);
        next.delete(blockId);
        return next;
      });
    }
  };

  return (
    <div className="notebook-canvas">
      {/* Header */}
      <div className="notebook-header">
        <h2 className="notebook-title">📖 {chapterTitle}</h2>
        <div className="entry-count">
          {entries.length} section{entries.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* Content Area */}
      <div className="notebook-content">
        {entries.length === 0 ? (
          <motion.div
            className="empty-state"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div className="empty-icon">📚</div>
            <p>No content yet. Ask a question or select a section to get started.</p>
          </motion.div>
        ) : (
          <motion.div
            className="blocks-container"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ staggerChildren: 0.1 }}
          >
            {entries.map((entry) => (
              <NotebookBlock
                key={entry.blockId}
                blockId={entry.blockId}
                topicRef={entry.topicRef}
                content={entry.content}
                onAskAI={handleAskAI}
                onUpdate={onUpdate}
                isUpdating={updatingBlocks.has(entry.blockId)}
              />
            ))}
          </motion.div>
        )}
      </div>

      {/* Footer */}
      {entries.length > 0 && (
        <motion.div
          className="notebook-footer"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <div className="footer-stat">
            <span className="stat-label">Total Sections:</span>
            <span className="stat-value">{entries.length}</span>
          </div>
          <div className="footer-stat">
            <span className="stat-label">Last Updated:</span>
            <span className="stat-value">
              {entries.length > 0
                ? new Date(entries[entries.length - 1].timestamp).toLocaleDateString()
                : 'N/A'}
            </span>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default NotebookCanvas;
