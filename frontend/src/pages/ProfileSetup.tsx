import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { InteractionSpeed } from '../types';
import './Auth.css';

const ProfileSetup = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [preferences, setPreferences] = useState({
    preferText: true,
    preferAudio: false,
    preferVisual: true,
    useExamples: true,
    useDiagrams: true,
    useAnalogies: true,
    simplifyLanguage: false,
    stepByStep: true,
    interactionSpeed: InteractionSpeed.MEDIUM as string,
    darkMode: false,
    fontSize: 'MEDIUM' as 'SMALL' | 'MEDIUM' | 'LARGE',
    reducedMotion: false,
    highContrast: false,
  });

  const handleToggle = (key: string) => {
    setPreferences((prev) => ({
      ...prev,
      [key]: !prev[key as keyof typeof prev],
    }));
  };

  const handleSelect = (key: string, value: string) => {
    setPreferences((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleNext = () => {
    if (step < 4) {
      setStep(step + 1);
    } else {
      localStorage.setItem('learningPreferences', JSON.stringify(preferences));
      navigate('/dashboard');
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card profile-setup-card">
        <div className="auth-header">
          <h1>🎨 Let's Personalize Your Experience</h1>
          <p>Hi {user?.name}! Tell us how you like to learn.</p>
          <div className="progress-bar">
            <div className="progress" style={{ width: `${(step / 4) * 100}%` }}></div>
          </div>
          <span className="step-indicator">Step {step} of 4</span>
        </div>

        <div className="setup-content">
          {step === 1 && (
            <div className="setup-step">
              <h2>📚 How do you like to receive information?</h2>
              <p className="step-description">Select all that work for you</p>
              
              <div className="preference-options">
                <button
                  type="button"
                  className={`preference-card ${preferences.preferText ? 'selected' : ''}`}
                  onClick={() => handleToggle('preferText')}
                >
                  <span className="icon">📝</span>
                  <span className="label">Text</span>
                  <span className="description">Read explanations</span>
                </button>
                
                <button
                  type="button"
                  className={`preference-card ${preferences.preferAudio ? 'selected' : ''}`}
                  onClick={() => handleToggle('preferAudio')}
                >
                  <span className="icon">🔊</span>
                  <span className="label">Audio</span>
                  <span className="description">Listen to explanations</span>
                </button>
                
                <button
                  type="button"
                  className={`preference-card ${preferences.preferVisual ? 'selected' : ''}`}
                  onClick={() => handleToggle('preferVisual')}
                >
                  <span className="icon">🖼️</span>
                  <span className="label">Visual</span>
                  <span className="description">See diagrams & images</span>
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="setup-step">
              <h2>🧠 How should I explain things?</h2>
              <p className="step-description">Choose your learning style</p>
              
              <div className="preference-toggles">
                <label className="toggle-option">
                  <span>Use real-world examples</span>
                  <input
                    type="checkbox"
                    checked={preferences.useExamples}
                    onChange={() => handleToggle('useExamples')}
                  />
                  <span className="toggle-slider"></span>
                </label>
                
                <label className="toggle-option">
                  <span>Include diagrams</span>
                  <input
                    type="checkbox"
                    checked={preferences.useDiagrams}
                    onChange={() => handleToggle('useDiagrams')}
                  />
                  <span className="toggle-slider"></span>
                </label>
                
                <label className="toggle-option">
                  <span>Use simple comparisons</span>
                  <input
                    type="checkbox"
                    checked={preferences.useAnalogies}
                    onChange={() => handleToggle('useAnalogies')}
                  />
                  <span className="toggle-slider"></span>
                </label>
                
                <label className="toggle-option">
                  <span>Use simpler words</span>
                  <input
                    type="checkbox"
                    checked={preferences.simplifyLanguage}
                    onChange={() => handleToggle('simplifyLanguage')}
                  />
                  <span className="toggle-slider"></span>
                </label>
                
                <label className="toggle-option">
                  <span>Break into small steps</span>
                  <input
                    type="checkbox"
                    checked={preferences.stepByStep}
                    onChange={() => handleToggle('stepByStep')}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="setup-step">
              <h2>⏱️ What pace works best for you?</h2>
              <p className="step-description">We'll adjust how fast we go</p>
              
              <div className="speed-options">
                <button
                  type="button"
                  className={`speed-card ${preferences.interactionSpeed === InteractionSpeed.SLOW ? 'selected' : ''}`}
                  onClick={() => handleSelect('interactionSpeed', InteractionSpeed.SLOW)}
                >
                  <span className="icon">🐢</span>
                  <span className="label">Take it slow</span>
                  <span className="description">More time to think</span>
                </button>
                
                <button
                  type="button"
                  className={`speed-card ${preferences.interactionSpeed === InteractionSpeed.MEDIUM ? 'selected' : ''}`}
                  onClick={() => handleSelect('interactionSpeed', InteractionSpeed.MEDIUM)}
                >
                  <span className="icon">🚶</span>
                  <span className="label">Comfortable pace</span>
                  <span className="description">Balanced timing</span>
                </button>
                
                <button
                  type="button"
                  className={`speed-card ${preferences.interactionSpeed === InteractionSpeed.FAST ? 'selected' : ''}`}
                  onClick={() => handleSelect('interactionSpeed', InteractionSpeed.FAST)}
                >
                  <span className="icon">🏃</span>
                  <span className="label">Quick learner</span>
                  <span className="description">Move faster</span>
                </button>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="setup-step">
              <h2>🎨 Make it comfortable</h2>
              <p className="step-description">Customize how things look</p>
              
              <div className="preference-toggles">
                <label className="toggle-option">
                  <span>🌙 Dark mode</span>
                  <input
                    type="checkbox"
                    checked={preferences.darkMode}
                    onChange={() => handleToggle('darkMode')}
                  />
                  <span className="toggle-slider"></span>
                </label>
                
                <label className="toggle-option">
                  <span>🔲 High contrast</span>
                  <input
                    type="checkbox"
                    checked={preferences.highContrast}
                    onChange={() => handleToggle('highContrast')}
                  />
                  <span className="toggle-slider"></span>
                </label>
                
                <label className="toggle-option">
                  <span>✨ Reduce animations</span>
                  <input
                    type="checkbox"
                    checked={preferences.reducedMotion}
                    onChange={() => handleToggle('reducedMotion')}
                  />
                  <span className="toggle-slider"></span>
                </label>
              </div>
              
              <div className="font-size-selector">
                <span>Text size:</span>
                <div className="size-buttons">
                  <button
                    type="button"
                    className={preferences.fontSize === 'SMALL' ? 'selected' : ''}
                    onClick={() => handleSelect('fontSize', 'SMALL')}
                  >
                    A
                  </button>
                  <button
                    type="button"
                    className={preferences.fontSize === 'MEDIUM' ? 'selected' : ''}
                    onClick={() => handleSelect('fontSize', 'MEDIUM')}
                  >
                    A
                  </button>
                  <button
                    type="button"
                    className={preferences.fontSize === 'LARGE' ? 'selected' : ''}
                    onClick={() => handleSelect('fontSize', 'LARGE')}
                  >
                    A
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="setup-navigation">
          {step > 1 && (
            <button type="button" className="nav-button back" onClick={handleBack}>
              ← Back
            </button>
          )}
          <button type="button" className="nav-button next" onClick={handleNext}>
            {step === 4 ? "Let's Start! 🚀" : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProfileSetup;
