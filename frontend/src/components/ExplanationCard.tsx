import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useLearning } from '../context/LearningContext';
import { chatApi, responsesApi } from '../api/client';
import './ExplanationCard.css';

interface ExplanationCardProps {
  id: string;
  topic: string;
  explanation: string;
  metaText?: string;
  liked?: boolean;
  iterationLevel: number;
  onFeedback: (cardId: string, liked: boolean) => Promise<void>;
}

export const ExplanationCard = ({
  id,
  topic,
  explanation,
  metaText,
  liked,
  iterationLevel,
  onFeedback,
}: ExplanationCardProps) => {
  const { showMetaText, setIsLoading, replaceCardExplanation } = useLearning();
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [showMetaToggle, setShowMetaToggle] = useState(false);

  const handleUnderstood = async () => {
    setIsLoading(true);
    try {
      await responsesApi.updateFeedback({
        response_id: id,
        liked: true,
        feedback_text: 'Student understood',
      });
      await onFeedback(id, true);
    } catch (error) {
      console.error('Error updating feedback:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDidntUnderstand = async () => {
    setIsLoading(true);
    setIsRegenerating(true);
    try {
      // Request simplified explanation from AI
      const response = await chatApi.sendMessage({
        content: `Please explain this more simply and in an autism-friendly way: "${topic}". Use very simple language, concrete examples, and avoid abstract concepts.`,
        input_type: 'TEXT',
      });

      // Store feedback first
      await responsesApi.updateFeedback({
        response_id: id,
        liked: false,
        feedback_text: 'Student needs clarification',
      });

      // Regenerate with new explanation
      await responsesApi.regenerateExplanation({
        response_id: id,
        new_explanation: response.message,
        new_content_text: response.message,
      });

      // Update local state with smooth animation
      replaceCardExplanation(id, response.message, iterationLevel + 1);
    } catch (error) {
      console.error('Error regenerating explanation:', error);
    } finally {
      setIsLoading(false);
      setIsRegenerating(false);
    }
  };

  return (
    <motion.div
      className="explanation-card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="card-header">
        <div className="topic-section">
          <h2 className="topic-title">📚 {topic}</h2>
          <span className="iteration-badge">Version {iterationLevel}</span>
        </div>
        {metaText && (
          <button
            className="meta-toggle-btn"
            onClick={() => setShowMetaToggle(!showMetaToggle)}
            title="Show/hide conversational context"
          >
            {showMetaToggle ? '👁️ Hide Context' : '👁️ Show Context'}
          </button>
        )}
      </div>

      {/* Meta Text (Collapsible) */}
      <AnimatePresence>
        {(showMetaText || showMetaToggle) && metaText && (
          <motion.div
            className="meta-text-section"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="meta-text-label">💬 Context (for caregivers)</div>
            <p className="meta-text-content">{metaText}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Explanation */}
      <AnimatePresence mode="wait">
        <motion.div
          key={explanation}
          className="explanation-content"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="explanation-text">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {explanation}
            </ReactMarkdown>
          </div>
        </motion.div>
      </AnimatePresence>

      {/* Feedback Buttons */}
      <div className="feedback-section">
        <motion.button
          className={`feedback-btn understood-btn ${liked === true ? 'active' : ''}`}
          onClick={handleUnderstood}
          disabled={isRegenerating}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <span className="btn-emoji">👍</span>
          <span className="btn-text">I Understood</span>
        </motion.button>

        <motion.button
          className={`feedback-btn confused-btn ${liked === false ? 'active' : ''}`}
          onClick={handleDidntUnderstand}
          disabled={isRegenerating}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <span className="btn-emoji">😕</span>
          <span className="btn-text">
            {isRegenerating ? 'Simplifying...' : 'I Didn\'t Understand'}
          </span>
        </motion.button>
      </div>

      {/* Status Indicators */}
      <div className="status-section">
        {liked === true && (
          <motion.div
            className="status-badge understood"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 200 }}
          >
            ✓ Understood
          </motion.div>
        )}
        {liked === false && (
          <motion.div
            className="status-badge confused"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 200 }}
          >
            ⚠ Needs Clarification
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

export default ExplanationCard;
