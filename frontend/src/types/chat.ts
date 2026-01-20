export type MessageRole = 'ai' | 'user' | 'assistant';
export type EmotionState = 'happy' | 'confused' | 'neutral';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  emotion?: EmotionState;
}

export interface ExplanationPart {
  id: string;
  title: string;
  content: string;
}

export interface InteractiveResponse {
  message: string;
  buttons: ResponseButton[];
  explanationParts?: ExplanationPart[];
  emotionPrompt?: string;
}

export interface ResponseButton {
  id: string;
  label: string;
  action: 'simplify' | 'detail' | 'summarize' | 'continue' | 'confused' | 'understood' | 'break' | 'stop';
  emoji?: string;
}

export interface ChatSession {
  sessionId: string;
  userId: string;
  messages: Message[];
  currentState: 'explaining' | 'waiting_feedback' | 'splitting' | 'paused';
}
