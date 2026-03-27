/**
 * API Configuration
 * 
 * Blueprint Project System - Environment Configuration
 * Switch between development and production Flask API endpoints
 * Payment Gateway: Flutterwave
 */

// Environment detection
const isDevelopment = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;

// API Base URLs - Update these when deploying
const API_URLS = {
  development: "http://localhost:5000/api",
  production: import.meta.env.VITE_API_BASE_URL || "https://your-production-api.com/api",
};

// Current API Base URL
export const API_BASE_URL = isDevelopment 
  ? API_URLS.development 
  : API_URLS.production;

// Flutterwave Configuration
export const FLUTTERWAVE_CONFIG = {
  PUBLIC_KEY: import.meta.env.VITE_FLUTTERWAVE_PUBLIC_KEY || "FLWPUBK_TEST-xxxxx",
  CURRENCY: "NGN", // Nigerian Naira (Flutterwave primary currency)
  COUNTRY: "NG",
  PAYMENT_OPTIONS: "card,banktransfer,ussd,mobilemoney",
};

// API Endpoints
export const API_ENDPOINTS = {
  // Authentication
  AUTH: {
    REGISTER: `${API_BASE_URL}/auth/register`,
    LOGIN: `${API_BASE_URL}/auth/login`,
    LOGOUT: `${API_BASE_URL}/auth/logout`,
    ME: `${API_BASE_URL}/auth/me`,
    REFRESH: `${API_BASE_URL}/auth/refresh`,
    FORGOT_PASSWORD: `${API_BASE_URL}/auth/forgot-password`,
    RESET_PASSWORD: `${API_BASE_URL}/auth/reset-password`,
    VERIFY_RESET_TOKEN: `${API_BASE_URL}/auth/verify-reset-token`,
  },
  
  // Users
  USERS: {
    BASE: `${API_BASE_URL}/users`,
    PROFILE: (id: string) => `${API_BASE_URL}/users/${id}`,
    UPDATE: (id: string) => `${API_BASE_URL}/users/${id}`,
  },
  
  // Artists
  ARTISTS: {
    BASE: `${API_BASE_URL}/artists`,
    DETAIL: (id: string) => `${API_BASE_URL}/artists/${id}`,
    SONGS: (id: string) => `${API_BASE_URL}/artists/${id}/songs`,
    CHECK_WINNER: (id: string) => `${API_BASE_URL}/artists/${id}/winner-status`,
  },
  
  // Songs
  SONGS: {
    BASE: `${API_BASE_URL}/songs`,
    DETAIL: (id: string) => `${API_BASE_URL}/songs/${id}`,
    UPLOAD: `${API_BASE_URL}/songs/upload`,
    APPROVE: (id: string) => `${API_BASE_URL}/songs/${id}/approve`,
    REJECT: (id: string) => `${API_BASE_URL}/songs/${id}/reject`,
  },
  
  // Votes
  VOTES: {
    BASE: `${API_BASE_URL}/votes`,
    CAST: `${API_BASE_URL}/votes`,
    CHECK: (songId: string) => `${API_BASE_URL}/votes/check/${songId}`,
    MY_VOTE: `${API_BASE_URL}/votes/my-vote`,
    HAS_VOTED: `${API_BASE_URL}/votes/has-voted`,
  },
  
  // Leaderboard
  LEADERBOARD: {
    BASE: `${API_BASE_URL}/leaderboard`,
    TOP: (limit: number) => `${API_BASE_URL}/leaderboard?limit=${limit}`,
  },
  
  // Contest
  CONTEST: {
    BASE: `${API_BASE_URL}/contest`,
    CURRENT: `${API_BASE_URL}/contest/current`,
    PHASES: `${API_BASE_URL}/contest/phases`,
    WINNERS: `${API_BASE_URL}/contest/winners`,
  },
  
  // Payments (Flutterwave)
  PAYMENTS: {
    INITIALIZE: `${API_BASE_URL}/payments/initialize`,
    VERIFY: `${API_BASE_URL}/payments/verify`,
    WEBHOOK: `${API_BASE_URL}/payments/webhook`,
    STATUS: (transactionId: string) => `${API_BASE_URL}/payments/status/${transactionId}`,
  },
  
  // Admin
  ADMIN: {
    DASHBOARD: `${API_BASE_URL}/admin/dashboard`,
    USERS: `${API_BASE_URL}/admin/users`,
    PENDING_SONGS: `${API_BASE_URL}/admin/songs/pending`,
    CONTESTS: `${API_BASE_URL}/admin/contests`,
    PAYMENTS: `${API_BASE_URL}/admin/payments`,
    WINNERS: `${API_BASE_URL}/admin/winners`,
  },
};

// App Configuration
export const APP_CONFIG = {
  // Artist Registration Fee (in Kobo for Flutterwave - Nigerian currency smallest unit)
  ARTIST_REGISTRATION_FEE: 25000, // ₦25,000.00 (or equivalent in your currency)
  ARTIST_REGISTRATION_FEE_DISPLAY: "₦25,000",
  CURRENCY: "NGN",
  CURRENCY_SYMBOL: "₦",
  
  // Contest Settings
  CONTEST_DURATION_MONTHS: 3,
  REGISTRATION_PERIOD_MONTHS: 2,
  VOTING_PERIOD_MONTHS: 1,
  
  // Voting Rules
  MAX_VOTES_PER_USER_PER_CONTEST: 1,
  
  // Winner Restrictions
  WINNER_CONTEST_COOLDOWN_MONTHS: 12, // Winners cannot participate for 12 months
  
  // File Upload Limits
  MAX_SONG_SIZE_MB: 15,
  ALLOWED_AUDIO_TYPES: ["audio/mpeg", "audio/mp3"],
  
  // Pagination
  DEFAULT_PAGE_SIZE: 10,
  LEADERBOARD_DEFAULT_LIMIT: 50,
};

// Security: Input validation schemas
export const VALIDATION = {
  EMAIL_REGEX: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  PASSWORD_MIN_LENGTH: 8,
  NAME_MAX_LENGTH: 100,
  ARTIST_NAME_MAX_LENGTH: 50,
  GENRE_MAX_LENGTH: 30,
};

// Security: Validation patterns for form inputs
export const VALIDATION_PATTERNS = {
  email: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
  password: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$/,
  username: /^[a-zA-Z0-9_]{3,30}$/,
  stageName: /^[a-zA-Z0-9\s-]{2,50}$/,
  phone: /^[+]?[0-9]{10,15}$/,
};

// Helper function for API calls with auth token
export const getAuthHeaders = (token?: string): HeadersInit => {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  
  return headers;
};

// Helper for multipart form data (file uploads)
export const getMultipartHeaders = (token?: string): HeadersInit => {
  const headers: HeadersInit = {};
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  
  return headers;
};

// Security: Sanitize user input
export const sanitizeInput = (input: string): string => {
  return input
    .trim()
    .replace(/[<>]/g, '') // Remove potential HTML tags
    .slice(0, 1000); // Limit length
};

// Security: Validate transaction reference
export const isValidTransactionRef = (ref: string): boolean => {
  return /^[a-zA-Z0-9_-]+$/.test(ref) && ref.length >= 10 && ref.length <= 100;
};

export default {
  API_BASE_URL,
  API_ENDPOINTS,
  APP_CONFIG,
  FLUTTERWAVE_CONFIG,
  VALIDATION,
  getAuthHeaders,
  getMultipartHeaders,
  sanitizeInput,
  isValidTransactionRef,
};
