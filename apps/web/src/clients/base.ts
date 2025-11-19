/**
 * Shared axios instance with automatic token refresh on 401 responses.
 * Uses axios-auth-refresh library to handle token refresh logic and request queuing.
 */

import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import createAuthRefreshInterceptor from 'axios-auth-refresh';

import { getAccessToken, refreshAuthLogic } from '@/clients/auth';
import { env } from '@/env';

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
      if (config.url?.includes('auth/') || config.url?.includes('auth.') || config.url?.includes('/auth') || (config as any).skipAuthRefresh) {
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

// Export singleton instance - base HTTP client used by all other API clients
export const baseClient = createApiClient();
