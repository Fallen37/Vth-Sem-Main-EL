import React from 'react';
import Avatar from './Avatar';
import './MessageBubble.css';
import type { Message, EmotionState } from '../types/chat';

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const getEmotionEmoji = (emotion?: EmotionState) => {
    switch (emotion) {
      case 'happy':
        return '😊';
      case 'confused':
        return '😕';
      case 'neutral':
      default:
        return '😐';
    }
  };

  return (
    <div className={`message-bubble-container message-${message.role}`}>
      <div className="message-avatar">
        <Avatar 
          role={message.role} 
          size="small" 
          emotion={message.emotion as any}
        />
      </div>
      
      <div className="message-content-wrapper">
        <div className={`message-bubble message-bubble-${message.role}`}>
          <div className="message-header">
            <span className="message-role">
              {message.role === 'ai' && '🤖 AI Tutor'}
              {message.role === 'user' && '👧 You'}
              {message.role === 'assistant' && '👩‍🏫 Guardian'}
            </span>
            {message.emotion && (
              <span className="message-emotion">
                {getEmotionEmoji(message.emotion)}
              </span>
            )}
          </div>
          <div className="message-text">
            {message.content}
          </div>
          <div className="message-time">
            {message.timestamp.toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit' 
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
