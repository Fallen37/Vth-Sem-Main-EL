import React from 'react';
import './ExplanationParts.css';
import type { ExplanationPart } from '../types/chat';

interface ExplanationPartsProps {
  parts: ExplanationPart[];
  onPartClick: (part: ExplanationPart) => void;
  isLoading?: boolean;
}

const ExplanationParts: React.FC<ExplanationPartsProps> = ({ 
  parts, 
  onPartClick, 
  isLoading = false 
}) => {
  return (
    <div className="explanation-parts-container">
      <div className="parts-header">
        <span className="parts-icon">🔍</span>
        <span className="parts-title">Which part confused you?</span>
      </div>
      
      <div className="parts-list">
        {parts.map((part: ExplanationPart, index: number) => (
          <button
            key={part.id}
            className="explanation-part-button"
            onClick={() => onPartClick(part)}
            disabled={isLoading}
          >
            <div className="part-number">{index + 1}</div>
            <div className="part-content">
              <div className="part-title">{part.title}</div>
              <div className="part-preview">{part.content.substring(0, 80)}...</div>
            </div>
            <div className="part-arrow">→</div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default ExplanationParts;
