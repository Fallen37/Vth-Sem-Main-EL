import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Profile.css';

const Profile = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  // User Info State
  const [username, setUsername] = useState(user?.name || '');
  const [grade, setGrade] = useState(user?.grade || 6);
  const [educationBoard, setEducationBoard] = useState('CBSE');
  const [gender, setGender] = useState('');
  const [avatar, setAvatar] = useState('/user-avatar-1.png');

  // Explicit Profiling State
  const [explicitProfile, setExplicitProfile] = useState(
    "I have low-level ADHD. I prefer detailed text responses sorted into points. I like text that has important parts highlighted. It makes it easier to read."
  );

  // Implicit Profiling (hardcoded for now)
  const implicitProfile = {
    format: "Responses organized in bullet points for easier scanning",
    length: "Short, direct steps without additional explanations",
    visualConsistency: "A single font style to avoid overstimulation",
    tone: "Concise and straightforward to accommodate the user's ADHD"
  };

  // Learning Progress (mock data for now)
  const progress = {
    completedLessons: 12,
    totalLessons: 50,
    percentage: 24,
    streak: 5,
    topicsCompleted: ['Fiber to Fabric', 'Acids and Bases'],
  };

  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  const avatarOptions = [
    { id: 1, path: '/user-avatar-1.png', name: 'Avatar 1' },
    { id: 2, path: '/user-avatar-2.png', name: 'Avatar 2' },
  ];

  const handleSaveChanges = async () => {
    setIsSaving(true);
    setSaveMessage('');

    try {
      // TODO: Update user info via API
      // await userApi.updateProfile({
      //   name: username,
      //   grade: grade,
      //   education_board: educationBoard,
      //   gender: gender,
      //   avatar: avatar,
      // });

      // TODO: Save explicit profile to backend
      // await profileApi.updateExplicitProfile(explicitProfile);

      setSaveMessage('✅ Changes saved successfully!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (error) {
      console.error('Error saving changes:', error);
      setSaveMessage('❌ Error saving changes. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="profile-container">
      {/* Header */}
      <header className="profile-header">
        <button className="back-btn" onClick={() => navigate('/dashboard')}>
          ← Dashboard
        </button>
        <h1 className="profile-title">👤 My Profile</h1>
        <div className="header-spacer"></div>
      </header>

      <div className="profile-content">
        {/* User Info Section */}
        <section className="profile-section user-info-section">
          <h2 className="section-title">📝 User Information</h2>
          
          <div className="info-grid">
            {/* Avatar Selection */}
            <div className="info-item avatar-item">
              <label className="info-label">Avatar</label>
              <div className="avatar-selector">
                <div className="current-avatar">
                  <img src={avatar} alt="Current Avatar" className="avatar-preview" />
                </div>
                <div className="avatar-options">
                  <div className="avatar-options-label">Choose Avatar:</div>
                  <div className="avatar-options-grid">
                    {avatarOptions.map((av) => (
                      <button
                        key={av.id}
                        className={`avatar-option ${avatar === av.path ? 'selected' : ''}`}
                        onClick={() => setAvatar(av.path)}
                        title={av.name}
                        type="button"
                      >
                        <img src={av.path} alt={av.name} className="avatar-option-img" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Username */}
            <div className="info-item">
              <label className="info-label">Username</label>
              <input
                type="text"
                className="info-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your name"
              />
            </div>

            {/* Grade */}
            <div className="info-item">
              <label className="info-label">Grade</label>
              <select
                className="info-select"
                value={grade}
                onChange={(e) => setGrade(Number(e.target.value))}
              >
                {[6, 7, 8, 9, 10, 11, 12].map((g) => (
                  <option key={g} value={g}>
                    Grade {g}
                  </option>
                ))}
              </select>
            </div>

            {/* Education Board */}
            <div className="info-item">
              <label className="info-label">Education Board</label>
              <select
                className="info-select"
                value={educationBoard}
                onChange={(e) => setEducationBoard(e.target.value)}
              >
                <option value="CBSE">CBSE</option>
                <option value="ICSE">ICSE</option>
                <option value="State">State Board</option>
                <option value="IB">IB</option>
                <option value="Other">Other</option>
              </select>
            </div>

            {/* Gender */}
            <div className="info-item">
              <label className="info-label">Gender</label>
              <div className="gender-options">
                {['Male', 'Female', 'Other', 'Prefer not to say'].map((g) => (
                  <label key={g} className="gender-option">
                    <input
                      type="radio"
                      name="gender"
                      value={g}
                      checked={gender === g}
                      onChange={(e) => setGender(e.target.value)}
                    />
                    <span>{g}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Learning Progress Section */}
        <section className="profile-section progress-section">
          <h2 className="section-title">📊 Learning Progress</h2>
          
          <div className="progress-grid">
            {/* Progress Circle */}
            <div className="progress-card main-progress-card">
              <div className="progress-circle">
                <svg viewBox="0 0 100 100">
                  <circle
                    className="progress-bg"
                    cx="50"
                    cy="50"
                    r="45"
                  />
                  <circle
                    className="progress-fill"
                    cx="50"
                    cy="50"
                    r="45"
                    strokeDasharray={`${progress.percentage * 2.827} 283`}
                  />
                </svg>
                <div className="progress-text">
                  <span className="progress-percentage">{progress.percentage}%</span>
                  <span className="progress-label">Complete</span>
                </div>
              </div>
              <div className="progress-details">
                <p>{progress.completedLessons} of {progress.totalLessons} lessons completed</p>
              </div>
            </div>

            {/* Streak Card */}
            <div className="progress-card streak-card">
              <div className="card-icon">🔥</div>
              <div className="card-content">
                <h3>{progress.streak} Day Streak</h3>
                <p>Keep it up!</p>
              </div>
            </div>

            {/* Topics Completed */}
            <div className="progress-card topics-card">
              <div className="card-icon">✅</div>
              <div className="card-content">
                <h3>Topics Mastered</h3>
                <ul className="topics-list">
                  {progress.topicsCompleted.map((topic, idx) => (
                    <li key={idx}>{topic}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* Profiling Section */}
        <section className="profile-section profiling-section">
          <h2 className="section-title">🧠 Learning Preferences</h2>

          {/* Implicit Profiling */}
          <div className="profiling-card implicit-card">
            <h3 className="profiling-title">
              <span className="profiling-icon">🤖</span>
              Implicit Profiling (AI-Detected)
            </h3>
            <p className="profiling-description">
              Based on your interaction patterns, we've detected the following preferences:
            </p>
            <div className="profiling-content">
              <div className="profiling-item">
                <strong>Format:</strong> {implicitProfile.format}
              </div>
              <div className="profiling-item">
                <strong>Length:</strong> {implicitProfile.length}
              </div>
              <div className="profiling-item">
                <strong>Visual Consistency:</strong> {implicitProfile.visualConsistency}
              </div>
              <div className="profiling-item">
                <strong>Tone:</strong> {implicitProfile.tone}
              </div>
            </div>
          </div>

          {/* Explicit Profiling */}
          <div className="profiling-card explicit-card">
            <h3 className="profiling-title">
              <span className="profiling-icon">✍️</span>
              Explicit Profiling (Your Input)
            </h3>
            <p className="profiling-description">
              Tell us about your learning preferences and needs:
            </p>
            <textarea
              className="profiling-textarea"
              value={explicitProfile}
              onChange={(e) => setExplicitProfile(e.target.value)}
              placeholder="Describe your learning preferences, challenges, and what helps you learn best..."
              rows={6}
            />
          </div>
        </section>

        {/* Save Button */}
        <div className="save-section">
          {saveMessage && (
            <div className={`save-message ${saveMessage.includes('✅') ? 'success' : 'error'}`}>
              {saveMessage}
            </div>
          )}
          <button
            className="save-btn"
            onClick={handleSaveChanges}
            disabled={isSaving}
          >
            {isSaving ? '💾 Saving...' : '💾 Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Profile;
