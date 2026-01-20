import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useLearning } from '../context/LearningContext';
import { responsesApi } from '../api/client';
import './LearningNotebook.css';

export const LearningNotebook = () => {
  const { notebookEntries, setNotebookEntries } = useLearning();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    loadNotebook();
  }, []);

  const loadNotebook = async () => {
    try {
      const data = await responsesApi.getNotebook();
      setNotebookEntries(data.notebook_entries || []);
    } catch (error) {
      console.error('Error loading notebook:', error);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const exportNotebook = () => {
    const content = notebookEntries
      .map((entry, index) => `${index + 1}. ${entry.topic}\n\n${entry.explanation}\n\n---\n\n`)
      .join('');

    const element = document.createElement('a');
    element.setAttribute('href', `data:text/plain;charset=utf-8,${encodeURIComponent(content)}`);
    element.setAttribute('download', `learning-notebook-${new Date().toISOString().split('T')[0]}.txt`);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="learning-notebook">
      {/* Header */}
      <div className="notebook-header">
        <div className="header-content">
          <h1 className="notebook-title">📖 My Learning Notebook</h1>
          <p className="notebook-subtitle">
            {notebookEntries.length} topic{notebookEntries.length !== 1 ? 's' : ''} mastered
          </p>
        </div>
        <motion.button
          className="export-btn"
          onClick={exportNotebook}
          disabled={notebookEntries.length === 0}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          📥 Export
        </motion.button>
      </div>

      {/* Empty State */}
      {notebookEntries.length === 0 && (
        <motion.div
          className="empty-state"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="empty-icon">📚</div>
          <h2>Your notebook is empty</h2>
          <p>Mark explanations as "I Understood" to add them to your learning notebook.</p>
        </motion.div>
      )}

      {/* Notebook Entries */}
      <div className="notebook-entries">
        {notebookEntries.map((entry, index) => (
          <motion.div
            key={entry.id}
            className="notebook-entry"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            {/* Entry Header */}
            <button
              className="entry-header"
              onClick={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
            >
              <div className="entry-number">{index + 1}</div>
              <div className="entry-info">
                <h3 className="entry-topic">{entry.topic}</h3>
                <p className="entry-meta">
                  Version {entry.iterationLevel} • {formatDate(entry.createdAt)}
                </p>
              </div>
              <div className="expand-icon">
                {expandedId === entry.id ? '▼' : '▶'}
              </div>
            </button>

            {/* Entry Content */}
            {expandedId === entry.id && (
              <motion.div
                className="entry-content"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
              >
                <div className="entry-text">
                  {entry.explanation}
                </div>
              </motion.div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Stats Footer */}
      {notebookEntries.length > 0 && (
        <motion.div
          className="notebook-stats"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <div className="stat">
            <span className="stat-label">Topics Mastered</span>
            <span className="stat-value">{notebookEntries.length}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Last Updated</span>
            <span className="stat-value">
              {formatDate(notebookEntries[0].createdAt)}
            </span>
          </div>
          <div className="stat">
            <span className="stat-label">Total Revisions</span>
            <span className="stat-value">
              {notebookEntries.reduce((sum, entry) => sum + entry.iterationLevel, 0)}
            </span>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default LearningNotebook;
