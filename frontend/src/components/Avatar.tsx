import React from 'react';
import './Avatar.css';

interface AvatarProps {
  role: 'ai' | 'user' | 'assistant';
  size?: 'small' | 'medium' | 'large';
  emotion?: 'happy' | 'confused' | 'neutral' | 'thinking';
}

const Avatar: React.FC<AvatarProps> = ({ role, size = 'medium', emotion = 'neutral' }) => {
  const getAvatarContent = () => {
    switch (role) {
      case 'ai':
        return (
          <div className={`avatar avatar-ai avatar-${size}`}>
            <div className="avatar-head">🤖</div>
            <div className={`avatar-expression emotion-${emotion}`}>
              {emotion === 'happy' && '😊'}
              {emotion === 'confused' && '🤔'}
              {emotion === 'thinking' && '💭'}
              {emotion === 'neutral' && '😐'}
            </div>
          </div>
        );
      case 'user':
        return (
          <div className={`avatar avatar-user avatar-${size}`}>
            <div className="avatar-head">👧</div>
            <div className={`avatar-expression emotion-${emotion}`}>
              {emotion === 'happy' && '😊'}
              {emotion === 'confused' && '😕'}
              {emotion === 'thinking' && '🤔'}
              {emotion === 'neutral' && '😐'}
            </div>
          </div>
        );
      case 'assistant':
        return (
          <div className={`avatar avatar-assistant avatar-${size}`}>
            <div className="avatar-head">👩‍🏫</div>
            <div className="avatar-label">Guardian</div>
          </div>
        );
      default:
        return null;
    }
  };

  return getAvatarContent();
};

export default Avatar;
