import { AuthenticationApi, Configuration, type User } from '@maive/api/client';
import axios from 'axios';

import { env } from '../env';

// Separate axios instance for auth operations to avoid circular interceptor issues
// This instance doesn't use the refresh interceptor to prevent infinite loops
const authAxios = axios.create({
  baseURL: env.PUBLIC_SERVER_URL,
  withCredentials: true,
});

const config = new Configuration({
  basePath: env.PUBLIC_SERVER_URL,
  baseOptions: { withCredentials: true },
});

const authApi = new AuthenticationApi(config, undefined, authAxios);

// Token cache - simple caching to avoid unnecessary refresh calls
let cachedToken: string | null = null;
let tokenExpiry: number = 0;

/**
 * Refresh access token by calling the backend auth endpoint.
 * Uses the generated API client with a separate axios instance.
 * This is called by the axios-auth-refresh interceptor when a 401 occurs.
 */
export async function refreshAccessToken(): Promise<string | null> {
  try {
    const response = await authApi.refreshTokenApiAuthRefreshPost();
    const token = response.data.session?.id_token;

    if (token) {
      cachedToken = token;
      // Cache for 15 minutes - balanced security/performance trade-off
      tokenExpiry = Date.now() + 15 * 60 * 1000;
      return token;
    }

    return null;
  } catch (error) {
    console.error('[Auth Client] Token refresh failed:', error);
    cachedToken = null;
    tokenExpiry = 0;
    return null;
  }
}

/**
 * Refresh logic for axios-auth-refresh interceptor.
 * This is called automatically when a 401 occurs.
 * The library handles all request queuing and prevents concurrent refreshes.
 *
 * @param failedRequest - The failed request object from axios-auth-refresh
 */
export async function refreshAuthLogic(failedRequest: any): Promise<void> {
  try {
    const token = await refreshAccessToken();

    if (token) {
      // Update the failed request's auth header so axios-auth-refresh can retry it
      failedRequest.response.config.headers.Authorization = `Bearer ${token}`;
      return Promise.resolve();
    }

    return Promise.reject(new Error('No token in refresh response'));
  } catch (error) {
    console.error('[Auth Client] Token refresh interceptor failed:', error);
    return Promise.reject(error);
  }
}

/**
 * Get cached token or fetch a new one if expired.
 * Used for initial requests (before any 401 occurs).
 */
export async function getAccessToken(): Promise<string | null> {
  const now = Date.now();

  // Return cached token if still valid
  if (cachedToken && now < tokenExpiry) {
    return cachedToken;
  }

  // Fetch a fresh token
  return refreshAccessToken();
}

/**
 * Clear the cached token. Useful for logout or error scenarios.
 */
export function clearCachedToken(): void {
  cachedToken = null;
  tokenExpiry = 0;
}

export async function getCurrentUser(): Promise<User | null> {
  try {
    const response = await authApi.getCurrentUserInfoApiAuthMeGet();
    return response.data;
  } catch {
    return null;
  }
}

export async function signOut(): Promise<void> {
  await authApi.signOutApiAuthSignoutPost();
  clearCachedToken();
}
