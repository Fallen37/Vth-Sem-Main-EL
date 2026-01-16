import axios from 'axios';

// Use relative URL so it works both in development and production
// In development with Vite proxy, or in production served from same origin
const API_BASE_URL = import.meta.env.DEV ? 'http://127.0.0.1:8001' : '';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth API
export const authApi = {
  register: async (data: {
    email: string;
    name: string;
    role: string;
    grade?: number;
    syllabus?: string;
  }) => {
    const response = await api.post('/auth/register', data);
    return response.data;
  },

  login: async (email: string) => {
    const response = await api.post('/auth/login', { email });
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

// Profile API
export const profileApi = {
  getProfile: async () => {
    const response = await api.get('/profile');
    return response.data;
  },

  updateProfile: async (data: any) => {
    const response = await api.put('/profile', data);
    return response.data;
  },

  getSessionPreferences: async () => {
    const response = await api.get('/profile/session-preferences');
    return response.data;
  },
};

// Progress API
export const progressApi = {
  getSummary: async () => {
    const response = await api.get('/progress/summary');
    return response.data;
  },

  getAchievements: async () => {
    const response = await api.get('/progress/achievements');
    return response.data;
  },

  getReviewTopics: async () => {
    const response = await api.get('/progress/review-topics');
    return response.data;
  },

  recordProgress: async (data: {
    topic_id: string;
    topic_name: string;
    grade: number;
    comprehension: number;
  }) => {
    const response = await api.post('/progress/record', data);
    return response.data;
  },
};

// Chat API
export const chatApi = {
  createSession: async () => {
    const response = await api.post('/chat/session');
    return response.data;
  },

  sendMessage: async (data: {
    session_id?: string;
    content: string;
    input_type?: string;
  }) => {
    const response = await api.post('/chat/message', data);
    return response.data;
  },

  submitComprehension: async (data: {
    session_id: string;
    feedback: string;
  }) => {
    const response = await api.post('/chat/comprehension', data);
    return response.data;
  },

  getComprehensionOptions: async () => {
    const response = await api.get('/chat/comprehension-options');
    return response.data;
  },

  getOutputModeOptions: async () => {
    const response = await api.get('/chat/output-mode-options');
    return response.data;
  },
};

// Content API
export const contentApi = {
  getDocuments: async (filters?: {
    grade?: number;
    syllabus?: string;
    subject?: string;
  }) => {
    const response = await api.get('/content/documents', { params: filters });
    return response.data;
  },

  getSummary: async () => {
    const response = await api.get('/content/summary');
    return response.data;
  },

  queryContent: async (data: {
    query: string;
    grade?: number;
    syllabus?: string;
    subject?: string;
    n_results?: number;
  }) => {
    const response = await api.post('/content/query', data);
    return response.data;
  },
};
