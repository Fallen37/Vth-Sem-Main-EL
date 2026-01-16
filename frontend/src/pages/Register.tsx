import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { authApi } from '../api/client';
import { UserRole, Syllabus } from '../types';
import './Auth.css';

const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    name: '',
    role: UserRole.STUDENT as string,
    grade: 5,
    syllabus: Syllabus.CBSE as string,
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRegistered, setIsRegistered] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState('');

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'grade' ? parseInt(value) : value,
    }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const data = {
        email: formData.email,
        name: formData.name,
        role: formData.role,
        ...(formData.role === UserRole.STUDENT && {
          grade: formData.grade,
          syllabus: formData.syllabus,
        }),
      };
      await authApi.register(data);
      setRegisteredEmail(formData.email);
      setIsRegistered(true);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Success screen after registration
  if (isRegistered) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="success-content">
            <div className="success-icon">🎉</div>
            <h1>Registration Successful!</h1>
            <p className="success-message">
              Welcome to Science Tutor! Your account has been created successfully.
            </p>
            <div className="registered-email">
              <span>📧</span>
              <span>{registeredEmail}</span>
            </div>
            <p className="next-step">
              You can now sign in with your email to start learning!
            </p>
            <Link to="/login" className="auth-button login-link">
              Go to Login →
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-card register-card">
        <div className="auth-header">
          <h1>🌟 Join Science Tutor</h1>
          <p>Create your account to start learning!</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="name">Your Name</label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="What should we call you?"
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="Enter your email"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="role">I am a...</label>
            <select
              id="role"
              name="role"
              value={formData.role}
              onChange={handleChange}
            >
              <option value={UserRole.STUDENT}>Student</option>
              <option value={UserRole.GUARDIAN}>Parent/Guardian</option>
            </select>
          </div>

          {formData.role === UserRole.STUDENT && (
            <>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="grade">Grade</label>
                  <select
                    id="grade"
                    name="grade"
                    value={formData.grade}
                    onChange={handleChange}
                  >
                    {[5, 6, 7, 8, 9, 10].map((g) => (
                      <option key={g} value={g}>
                        Grade {g}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="syllabus">Syllabus</label>
                  <select
                    id="syllabus"
                    name="syllabus"
                    value={formData.syllabus}
                    onChange={handleChange}
                  >
                    <option value={Syllabus.CBSE}>CBSE</option>
                    <option value={Syllabus.STATE}>State Board</option>
                  </select>
                </div>
              </div>
            </>
          )}

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="auth-button" disabled={isLoading}>
            {isLoading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Already have an account?{' '}
            <Link to="/login">Sign in here</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;
