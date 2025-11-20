import * as v from 'valibot';

export const CLIENT_ENV_PREFIX = 'PUBLIC_';

export const envSchema = v.object({
  /**
   * This is the backend API server. Note that this should be passed as
   * a build-time variable (ARG) in docker.
   */
  PUBLIC_SERVER_URL: v.pipe(v.string(), v.url()),

  /**
   * Set this if you want to run or deploy your app at a base URL. This is
   * usually required for deploying a repository to Github/Gitlab pages.
   */
  PUBLIC_BASE_PATH: v.pipe(v.optional(v.string(), '/'), v.startsWith('/')),

  /**
   * AWS Cognito domain URL for authentication
   */
  PUBLIC_COGNITO_DOMAIN: v.pipe(v.string(), v.url()),

  /**
   * AWS Cognito client ID for the application
   */
  PUBLIC_COGNITO_CLIENT_ID: v.string(),

  /**
   * AWS Cognito scopes for authentication
   */
  PUBLIC_COGNITO_SCOPES: v.optional(v.string(), 'openid+email+profile'),

  /**
   * The OAuth redirect route for Cognito.
   */
  PUBLIC_OAUTH_REDIRECT_ROUTE: v.string(),

  /**
   * Feature flag to enable/disable workflow functionality
   */
  PUBLIC_ENABLE_WORKFLOWS: v.optional(
    v.pipe(
      v.string(),
      v.transform((s) => s.toLowerCase() !== 'false'),
    ),
    'false',
  ),

  /**
   * Feature flag to enable/disable demo project creation (Mock CRM only)
   */
  PUBLIC_ENABLE_DEMO_PROJECT_CREATION: v.optional(
    v.pipe(
      v.string(),
      v.transform((s) => s.toLowerCase() === 'true'),
    ),
    'false',
  ),

  /**
   * Feature flag to enable/disable voice AI functionality (Projects and Phone Input tabs)
   */
  PUBLIC_ENABLE_VOICE_AI: v.optional(
    v.pipe(
      v.string(),
      v.transform((s) => s.toLowerCase() === 'true'),
    ),
    'false',
  ),

  /**
   * Feature flag to enable/disable call list functionality
   */
  PUBLIC_ENABLE_CALL_LIST: v.optional(
    v.pipe(
      v.string(),
      v.transform((s) => s.toLowerCase() === 'true'),
    ),
    'true',
  ),

  /**
   * PostHog API key for analytics
   */
  PUBLIC_POSTHOG_KEY: v.string(),

  /**
   * PostHog host URL (defaults to cloud)
   */
  PUBLIC_POSTHOG_HOST: v.optional(
    v.pipe(v.string(), v.url()),
    'https://app.posthog.com',
  ),
});

export const env = v.parse(envSchema, import.meta.env);

// Cognito configuration
export const COGNITO_DOMAIN = env.PUBLIC_COGNITO_DOMAIN;
export const COGNITO_CLIENT_ID = env.PUBLIC_COGNITO_CLIENT_ID;
export const COGNITO_SCOPES = env.PUBLIC_COGNITO_SCOPES;
export const COGNITO_CALLBACK_URL = `${env.PUBLIC_SERVER_URL}/${env.PUBLIC_OAUTH_REDIRECT_ROUTE.replace(/^\//, '')}`;
export const COGNITO_SIGN_IN_URL = `${COGNITO_DOMAIN}/login?client_id=${COGNITO_CLIENT_ID}&response_type=code&scope=${COGNITO_SCOPES}&redirect_uri=${encodeURIComponent(
  COGNITO_CALLBACK_URL,
)}`;

// PostHog configuration
export const POSTHOG_API_KEY = env.PUBLIC_POSTHOG_KEY;
export const POSTHOG_API_HOST = env.PUBLIC_POSTHOG_HOST;
