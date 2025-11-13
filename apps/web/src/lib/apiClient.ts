/**
 * Shared axios instance with automatic token refresh on 401 responses.
 * Uses axios-auth-refresh library to handle token refresh logic and request queuing.
 */

import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import createAuthRefreshInterceptor from 'axios-auth-refresh';

import { env } from '@/env';

// Token cache - simple caching to avoid unnecessary refresh calls
let cachedToken: string | null = null;
let tokenExpiry: number = 0;

/**
 * Refresh access token by calling the backend auth endpoint.
 * This is called automatically by axios-auth-refresh when a 401 occurs.
 * The library handles all request queuing and prevents concurrent refreshes.
 */
const refreshAuthLogic = async (failedRequest: any) => {
  try {
    const response = await axios.post(
      `${env.PUBLIC_SERVER_URL}/api/auth/refresh`,
      {},
      {
        withCredentials: true,
        skipAuthRefresh: true, // Don't intercept this request
      } as any
    );

    const token = response.data.session?.id_token;

    if (token) {
      cachedToken = token;
      // Cache for 15 minutes - balanced security/performance trade-off
      tokenExpiry = Date.now() + 15 * 60 * 1000;

      // Update the failed request's auth header so axios-auth-refresh can retry it
      failedRequest.response.config.headers.Authorization = `Bearer ${token}`;
      return Promise.resolve();
    }

    return Promise.reject(new Error('No token in refresh response'));
  } catch (error) {
    console.error('[API Client] Token refresh failed:', error);
    cachedToken = null;
    tokenExpiry = 0;
    return Promise.reject(error);
  }
};

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
  try {
    const response = await axios.post(
      `${env.PUBLIC_SERVER_URL}/api/auth/refresh`,
      {},
      {
        withCredentials: true,
        skipAuthRefresh: true,
      } as any
    );

    const token = response.data.session?.id_token;
    if (token) {
      cachedToken = token;
      // Cache for 15 minutes - balanced security/performance trade-off
      tokenExpiry = Date.now() + 15 * 60 * 1000;
      return token;
    }
  } catch (error) {
    console.error('[API Client] Token fetch failed:', error);
  }

  return null;
}

/**
 * Create and configure the shared axios instance with automatic token refresh.
 * Uses axios-auth-refresh library to handle:
 * - Automatic retry on 401 responses
 * - Request queuing during token refresh
 * - Prevention of concurrent refresh requests
 */
export function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: env.PUBLIC_SERVER_URL,
    withCredentials: true,
  });

  // Setup automatic token refresh on 401 responses
  // This library handles ALL the queue management, race conditions, and retry logic!
  createAuthRefreshInterceptor(client, refreshAuthLogic, {
    statusCodes: [401], // Refresh on 401 Unauthorized
    pauseInstanceWhileRefreshing: true, // Pause all requests while refreshing to prevent race conditions
  });

  // Request interceptor: Add access token to requests
  client.interceptors.request.use(
    async (config: InternalAxiosRequestConfig) => {
      // Skip auth endpoints and requests marked with skipAuthRefresh
      if (config.url?.includes('/api/auth/') || (config as any).skipAuthRefresh) {
        return config;
      }

      const token = await getAccessToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      return config;
    },
    (error) => Promise.reject(error)
  );

  return client;
}

// Export singleton instance
export const apiClient = createApiClient();
