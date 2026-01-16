import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import './Dashboard.css';

const Upload = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const [file, setFile] = useState<File | null>(null);
  const [formData, setFormData] = useState({
    grade: user?.grade || 8,
    syllabus: user?.syllabus || 'cbse',
    subject: 'Physics',
    chapter: '',
    content_type: 'textbook',
    topic: '',
    tags: '',
  });
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select a file');
      return;
    }

    setIsUploading(true);
    setError('');
    setMessage('');

    try {
      const uploadData = new FormData();
      uploadData.append('file', file);
      uploadData.append('grade', formData.grade.toString());
      uploadData.append('syllabus', formData.syllabus);
      uploadData.append('subject', formData.subject);
      uploadData.append('chapter', formData.chapter);
      uploadData.append('content_type', formData.content_type);
      if (formData.topic) uploadData.append('topic', formData.topic);
      if (formData.tags) uploadData.append('tags', formData.tags);

      const response = await api.post('/content/upload', uploadData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.status === 'ready') {
        setMessage(`✅ File uploaded and processed successfully!\n\nDocument ID: ${response.data.document_id}\n\nYou can now ask questions about this content in the chat!`);
      } else if (response.data.status === 'failed') {
        setMessage(`⚠️ File uploaded but processing failed.\n\nDocument ID: ${response.data.document_id}\n\nPlease try uploading again or contact support.`);
      } else {
        setMessage(`✅ File uploaded successfully!\n\nDocument ID: ${response.data.document_id}\n\nProcessing... This may take a moment.`);
      }
      
      setFile(null);
      setFormData(prev => ({ ...prev, chapter: '', topic: '', tags: '' }));
      
      // Reset file input
      const fileInput = document.getElementById('file-input') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
      
    } catch (err: any) {
      console.error('Upload error:', err);
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <button className="back-button" onClick={() => navigate('/dashboard')}>
          ← Back to Dashboard
        </button>
        <div>
          <h1>📤 Upload Learning Material</h1>
          <p>Add textbooks, notes, or study materials</p>
        </div>
      </header>

      <div className="dashboard-content">
        <div className="upload-section" style={{ maxWidth: '600px', margin: '0 auto' }}>
          <form onSubmit={handleSubmit} className="upload-form">
            
            <div className="form-group">
              <label htmlFor="file-input">📄 Select File *</label>
              <input
                id="file-input"
                type="file"
                onChange={handleFileChange}
                accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
                required
                style={{ padding: '10px', border: '2px dashed #ccc', borderRadius: '8px' }}
              />
              <small>Supported: PDF, DOCX, TXT, Images</small>
              {file && <p style={{ color: '#4CAF50', marginTop: '8px' }}>✓ {file.name}</p>}
            </div>

            <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div className="form-group">
                <label htmlFor="grade">Grade *</label>
                <select
                  id="grade"
                  name="grade"
                  value={formData.grade}
                  onChange={handleChange}
                  required
                >
                  {[5, 6, 7, 8, 9, 10].map(g => (
                    <option key={g} value={g}>Grade {g}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="syllabus">Syllabus *</label>
                <select
                  id="syllabus"
                  name="syllabus"
                  value={formData.syllabus}
                  onChange={handleChange}
                  required
                >
                  <option value="cbse">CBSE</option>
                  <option value="state">State Board</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="subject">Subject *</label>
              <select
                id="subject"
                name="subject"
                value={formData.subject}
                onChange={handleChange}
                required
              >
                <option value="Physics">Physics</option>
                <option value="Chemistry">Chemistry</option>
                <option value="Biology">Biology</option>
                <option value="Mathematics">Mathematics</option>
                <option value="General Science">General Science</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="chapter">Chapter *</label>
              <input
                type="text"
                id="chapter"
                name="chapter"
                value={formData.chapter}
                onChange={handleChange}
                placeholder="e.g., Force and Motion"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="topic">Topic (Optional)</label>
              <input
                type="text"
                id="topic"
                name="topic"
                value={formData.topic}
                onChange={handleChange}
                placeholder="e.g., Newton's Laws"
              />
            </div>

            <div className="form-group">
              <label htmlFor="content_type">Content Type *</label>
              <select
                id="content_type"
                name="content_type"
                value={formData.content_type}
                onChange={handleChange}
                required
              >
                <option value="textbook">Textbook</option>
                <option value="notes">Notes</option>
                <option value="past_paper">Past Paper</option>
                <option value="question_bank">Question Bank</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="tags">Tags (Optional)</label>
              <input
                type="text"
                id="tags"
                name="tags"
                value={formData.tags}
                onChange={handleChange}
                placeholder="e.g., important, exam, revision (comma-separated)"
              />
            </div>

            {message && (
              <div style={{ padding: '12px', background: '#e8f5e9', color: '#2e7d32', borderRadius: '8px', marginBottom: '16px' }}>
                {message}
              </div>
            )}

            {error && (
              <div style={{ padding: '12px', background: '#ffebee', color: '#c62828', borderRadius: '8px', marginBottom: '16px' }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              className="primary-button"
              disabled={isUploading || !file}
              style={{ width: '100%', padding: '12px', fontSize: '16px' }}
            >
              {isUploading ? '⏳ Uploading...' : '📤 Upload Document'}
            </button>
          </form>

          <div style={{ marginTop: '32px', padding: '16px', background: '#f5f5f5', borderRadius: '8px' }}>
            <h3>ℹ️ How it works:</h3>
            <ol style={{ marginLeft: '20px' }}>
              <li>Upload your document (PDF, DOCX, TXT, or image)</li>
              <li>System will process and extract the content</li>
              <li>Content will be available in the chatbot</li>
              <li>Students can ask questions about uploaded materials</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Upload;
