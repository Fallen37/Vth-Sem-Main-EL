// User types - using const objects instead of enums for erasableSyntaxOnly
export const UserRole = {
  STUDENT: 'student',
  GUARDIAN: 'guardian',
  ADMIN: 'admin',
} as const;
export type UserRole = typeof UserRole[keyof typeof UserRole];

export const Syllabus = {
  CBSE: 'cbse',
  STATE: 'state',
} as const;
export type Syllabus = typeof Syllabus[keyof typeof Syllabus];

export const InteractionSpeed = {
  SLOW: 'slow',
  MEDIUM: 'medium',
  FAST: 'fast',
} as const;
export type InteractionSpeed = typeof InteractionSpeed[keyof typeof InteractionSpeed];

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  grade?: number;
  syllabus?: Syllabus;
}

export interface AuthResponse {
  user_id: string;
  token: string;
  user: User;
}

export interface RegisterData {
  email: string;
  name: string;
  role: UserRole;
  grade?: number;
  syllabus?: Syllabus;
}

export interface LoginData {
  email: string;
}

// Learning Profile types
export interface OutputMode {
  text: boolean;
  audio: boolean;
  visual: boolean;
}

export interface ExplanationStyle {
  use_examples: boolean;
  use_diagrams: boolean;
  use_analogies: boolean;
  simplify_language: boolean;
  step_by_step: boolean;
}

export interface InterfacePreferences {
  dark_mode: boolean;
  font_size: 'SMALL' | 'MEDIUM' | 'LARGE';
  reduced_motion: boolean;
  high_contrast: boolean;
}

export interface LearningProfile {
  id: string;
  user_id: string;
  preferred_output_mode: OutputMode;
  preferred_explanation_style: ExplanationStyle;
  interaction_speed: InteractionSpeed;
  interface_preferences: InterfacePreferences;
}
