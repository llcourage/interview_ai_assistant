/**
 * API Configuration
 * Desktop version: All API requests go to Vercel backend
 * Web version: Uses current origin (Vercel) or Vercel API URL
 */
import { isElectron } from '../utils/isElectron';

// Hard clean function: ensure URL has no leading/trailing whitespace
const clean = (s?: string) => (s ?? "").trim();

// Vercel API URL (used by Desktop version and as fallback)
const DEFAULT_VERCEL_API_URL = clean('https://www.desktopai.org');

export const getApiBaseUrl = (): string => {
  // If environment variable is set, use it (highest priority)
  const viteApiUrl = clean(import.meta.env.VITE_API_URL);
  if (viteApiUrl) {
    console.log('🔧 API_BASE_URL: Using VITE_API_URL from env:', viteApiUrl);
    return viteApiUrl;
  }
  
  // Production mode
  if (import.meta.env.MODE === 'production') {
    // Electron desktop version: always use Vercel API
    if (isElectron()) {
      console.log('🔧 API_BASE_URL: Production Electron, using Vercel:', DEFAULT_VERCEL_API_URL);
      return DEFAULT_VERCEL_API_URL;
    }
    // Web version: use current origin (if deployed on Vercel, will use Vercel domain)
    const origin = clean(window.location.origin);
    console.log('🔧 API_BASE_URL: Production Web, using origin:', origin);
    return origin;
  }
  
  // Development mode: use Vercel API (can be overridden with VITE_API_URL)
  console.log('🔧 API_BASE_URL: DEV mode, using Vercel:', DEFAULT_VERCEL_API_URL);
  return DEFAULT_VERCEL_API_URL;
};

export const API_BASE_URL = getApiBaseUrl();

// Print final API URL used (once only)
console.log('🌐 API Base URL configured:', API_BASE_URL);
console.log('🌐 Environment:', {
  DEV: import.meta.env.DEV,
  MODE: import.meta.env.MODE,
  VITE_API_URL: import.meta.env.VITE_API_URL,
  isElectron: isElectron(),
  origin: typeof window !== 'undefined' ? window.location.origin : 'N/A'
});

/**
 * Enhanced fetch function that automatically adds Authorization header
 * for authenticated requests in Electron environment
 */
export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  // Get token from localStorage (if available)
  let authHeader: string | null = null;
  try {
    const { getAuthHeader } = await import('./auth');
    authHeader = getAuthHeader();
  } catch (e) {
    // auth module not available or token not found
    console.debug('No auth token available for API request');
  }

  // Merge headers
  const headers = new Headers(init.headers || {});
  if (authHeader) {
    headers.set('Authorization', authHeader);
  }

  // Build full URL
  const url = input.startsWith('http') ? input : `${API_BASE_URL}${input}`;

  // Make request with merged headers
  return fetch(url, {
    ...init,
    headers,
    credentials: 'include', // Include cookies for web version
  });
}


