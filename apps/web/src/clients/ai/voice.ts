// Voice AI client - handles voice AI API calls

import {
  Configuration,
  TwilioApi,
  VoiceAIApi,
  type ActiveCallResponse,
  type CallRequest,
  type CallResponse,
} from '@maive/api/client';
import {
  useMutation,
  useQuery,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query';

import { env } from '@/env';
import { baseClient } from '../base';

// Re-export types from the generated client
export type { ActiveCallResponse, CallRequest, CallResponse };

/**
 * Create a configured Voice AI API instance using the shared axios client
 */
const createVoiceAIApi = (): VoiceAIApi => {
  return new VoiceAIApi(
    new Configuration({
      basePath: env.PUBLIC_SERVER_URL,
    }),
    undefined,
    baseClient,
  );
};

/**
 * Create a configured Twilio API instance using the shared axios client
 */
const createTwilioApi = (): TwilioApi => {
  return new TwilioApi(
    new Configuration({
      basePath: env.PUBLIC_SERVER_URL,
    }),
    undefined,
    baseClient,
  );
};

/**
 * Get call status by call ID
 */
export async function getCallStatus(callId: string): Promise<CallResponse> {
  const api = createVoiceAIApi();

  const response = await api.getCallStatusApiVoiceAiCallsCallIdGet(callId);
  return response.data;
}

/**
 * Get user's active call (if any)
 */
export async function getActiveCall(): Promise<ActiveCallResponse | null> {
  const api = createVoiceAIApi();
  const response = await api.getActiveCallApiVoiceAiCallsActiveGet();
  return response.data; // Will be null if no active call
}

/**
 * Get Twilio access token for browser-based calling
 */
export async function getTwilioToken(): Promise<string> {
  const api = createTwilioApi();
  const response = await api.getTokenApiVoiceAiTwilioTokenGet();
  const token = response.data.token;
  if (!token) {
    throw new Error('No token received from server');
  }
  return token;
}

/**
 * Get the configured Voice AI provider
 */
export async function getVoiceAIProvider(): Promise<string> {
  const api = createVoiceAIApi();
  const response = await api.getProviderApiVoiceAiProviderGet();
  return response.data.provider;
}

/**
 * End an ongoing call by call ID
 */
export async function endCall(callId: string): Promise<void> {
  const api = createVoiceAIApi();

  await api.endCallApiVoiceAiCallsCallIdDelete(callId);
}

/**
 * React Query hook for getting active call
 */
export function useActiveCall(options?: {
  enabled?: boolean;
}): UseQueryResult<ActiveCallResponse | null, Error> {
  return useQuery({
    queryKey: ['active-call'],
    queryFn: getActiveCall,
    enabled: options?.enabled !== false,
    staleTime: 5000, // Consider data fresh for 5 seconds
  });
}

/**
 * React Query hook for polling call status
 */
export function useCallStatus(
  callId: string | null,
  options?: { enabled?: boolean; refetchInterval?: number },
): UseQueryResult<CallResponse, Error> {
  return useQuery({
    queryKey: ['call-status', callId],
    queryFn: () => getCallStatus(callId!),
    enabled: options?.enabled !== false && callId !== null,
    refetchInterval: options?.refetchInterval ?? 3000, // Poll every 3 seconds by default
    refetchIntervalInBackground: true,
  });
}

/**
 * React Query hook for getting the configured Voice AI provider
 */
export function useVoiceAIProvider(): UseQueryResult<string, Error> {
  return useQuery({
    queryKey: ['voice-ai-provider'],
    queryFn: getVoiceAIProvider,
    staleTime: Infinity, // Provider doesn't change during session
  });
}

/**
 * React Query mutation hook for ending calls
 */
export function useEndCall(): UseMutationResult<void, Error, string> {
  return useMutation({
    mutationFn: endCall,
    onSuccess: () => {
      console.log('Voice AI call ended successfully');
    },
    onError: (error) => {
      console.error('Failed to end voice AI call:', error);
    },
  });
}
