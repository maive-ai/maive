// Voice AI client - handles voice AI API calls

import {
    Configuration,
    VoiceAIApi,
    type ActiveCallState,
    type CallRequest,
    type CallResponse,
} from '@maive/api/client';
import { useMutation, useQuery, type UseMutationResult, type UseQueryResult } from '@tanstack/react-query';

import { getIdToken } from '@/auth';
import { env } from '@/env';

// Re-export types from the generated client
export type { ActiveCallState, CallRequest, CallResponse };

/**
 * Create a configured Voice AI API instance
 */
const createVoiceAIApi = async (): Promise<VoiceAIApi> => {
  const token = await getIdToken();
  if (!token) throw new Error('Not authenticated');

  return new VoiceAIApi(
    new Configuration({
      accessToken: token,
      basePath: env.PUBLIC_SERVER_URL,
      baseOptions: { withCredentials: true },
    }),
  );
};

/**
 * Get call status by call ID
 */
export async function getCallStatus(callId: string): Promise<CallResponse> {
  const api = await createVoiceAIApi();

  const response = await api.getCallStatusApiVoiceAiCallsCallIdGet(callId);
  return response.data;
}

/**
 * Get user's active call (if any)
 */
export async function getActiveCall(): Promise<ActiveCallState | null> {
  const api = await createVoiceAIApi();
  const response = await api.getActiveCallApiVoiceAiCallsActiveGet();
  return response.data; // Will be null if no active call
}

/**
 * End an ongoing call by call ID
 */
export async function endCall(callId: string): Promise<void> {
  const api = await createVoiceAIApi();

  await api.endCallApiVoiceAiCallsCallIdDelete(callId);
}

/**
 * React Query hook for getting active call
 */
export function useActiveCall(options?: { enabled?: boolean }): UseQueryResult<ActiveCallState | null, Error> {
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
  options?: { enabled?: boolean; refetchInterval?: number }
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
