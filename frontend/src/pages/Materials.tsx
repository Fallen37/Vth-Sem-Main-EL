import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { contentApi } from '../api/client';
import './Dashboard.css';

interface Document {
  id: string;
  filename: string;
  subject: string;
  chapter: string;
  topic?: string;
  grade: number;
  syllabus: string;
  uploaded_at: string;
}

const Materials = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const subject = searchParams.get('subject') || 'All';
  
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDocuments();
  }, [subject]);

  const loadDocuments = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const filters: any = {};
      if (user?.grade) filters.grade = user.grade;
      if (user?.syllabus) filters.syllabus = user.syllabus;
      if (subject && subject !== 'All') filters.subject = subject;
      
      const response = await contentApi.getDocuments(filters);
      setDocuments(response.documents || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
      setError('Failed to load materials');
    } finally {
      setIsLoading(false);
    }
  };

  const subjects = ['All', 'Physics', 'Chemistry', 'Biology'];

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <button className="back-button" onClick={() => navigate('/dashboard')}>
          ← Back to Dashboard
        </button>
        <div>
          <h1>📚 Learning Materials</h1>
          <p>Browse your curriculum content</p>
        </div>
      </header>

      <div className="dashboard-content">
        {/* Subject Filter */}
        <div className="filter-section">
          <h3>Filter by Subject:</h3>
          <div className="subject-filters">
            {subjects.map(s => (
              <button
                key={s}
                className={`filter-btn ${subject === s ? 'active' : ''}`}
                onClick={() => navigate(`/materials?subject=${s}`)}
              >
                {s === 'Physics' ? '⚡' : s === 'Chemistry' ? '🧪' : s === 'Biology' ? '🧬' : '📖'} {s}
              </button>
            ))}
          </div>
        </div>

        {/* Materials List */}
        <div className="materials-section">
          {isLoading ? (
            <div className="loading-state">
              <div className="loading-spinner">📚</div>
              <p>Loading materials...</p>
            </div>
          ) : error ? (
            <div className="error-state">
              <p className="error-message">{error}</p>
            </div>
          ) : documents.length > 0 ? (
            <div className="materials-grid">
              {documents.map(doc => (
                <div key={doc.id} className="material-card">
                  <div className="material-header">
                    <span className="material-icon">
                      {doc.subject.toLowerCase().includes('physics') ? '⚡' :
                       doc.subject.toLowerCase().includes('chemistry') ? '🧪' :
                       doc.subject.toLowerCase().includes('biology') ? '🧬' : '📖'}
                    </span>
                    <div>
                      <h3>{doc.subject}</h3>
                      <p className="material-chapter">{doc.chapter}</p>
                      {doc.topic && <p className="material-topic">{doc.topic}</p>}
                    </div>
                  </div>
                  <div className="material-meta">
                    <span>Grade {doc.grade}</span>
                    <span>{doc.syllabus}</span>
                  </div>
                  <button 
                    className="material-action-btn"
                    onClick={() => navigate('/chat')}
                  >
                    Ask Questions →
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">📚</div>
              <h2>No Materials Yet</h2>
              <p>
                {subject !== 'All' 
                  ? `No ${subject} materials have been uploaded yet.`
                  : 'No learning materials have been uploaded yet.'}
              </p>
              <p className="empty-hint">
                Your teacher or administrator can upload curriculum content through the API.
              </p>
              <button 
                className="primary-button"
                onClick={() => navigate('/chat')}
              >
                Ask Science Buddy Instead →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Materials;
