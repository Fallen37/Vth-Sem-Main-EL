import React from 'react';
import './ResponseButtons.css';
import type { ResponseButton } from '../types/chat';

interface ResponseButtonsProps {
  buttons: ResponseButton[];
  onButtonClick: (button: ResponseButton) => void;
  isLoading?: boolean;
}

const ResponseButtons: React.FC<ResponseButtonsProps> = ({ 
  buttons, 
  onButtonClick, 
  isLoading = false 
}) => {
  const getButtonEmoji = (action: string) => {
    switch (action) {
      case 'simplify':
        return '📝';
      case 'detail':
        return '🔍';
      case 'summarize':
        return '📋';
      case 'continue':
        return '➡️';
      case 'confused':
        return '😕';
      case 'understood':
        return '👍';
      case 'break':
        return '⏸️';
      case 'stop':
        return '⏹️';
      default:
        return '💬';
    }
  };

  const getButtonColor = (action: string) => {
    switch (action) {
      case 'simplify':
        return 'button-simplify';
      case 'detail':
        return 'button-detail';
      case 'summarize':
        return 'button-summarize';
      case 'continue':
        return 'button-continue';
      case 'confused':
        return 'button-confused';
      case 'understood':
        return 'button-understood';
      case 'break':
        return 'button-break';
      case 'stop':
        return 'button-stop';
      default:
        return 'button-default';
    }
  };

  return (
    <div className="response-buttons-container">
      <div className="buttons-grid">
        {buttons.map((button: ResponseButton) => (
          <button
            key={button.id}
            className={`response-button ${getButtonColor(button.action)}`}
            onClick={() => onButtonClick(button)}
            disabled={isLoading}
            title={button.label}
          >
            <span className="button-emoji">
              {button.emoji || getButtonEmoji(button.action)}
            </span>
            <span className="button-label">
              {button.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default ResponseButtons;
