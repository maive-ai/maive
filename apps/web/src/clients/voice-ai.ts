// Voice AI client - using generated API client

import {
  Configuration,
  VoiceAIApi,
  type CallRequest,
  type CallResponse,
} from '@maive/api/client';
import { useMutation, useQuery, type UseMutationResult, type UseQueryResult } from '@tanstack/react-query';

import { getIdToken } from '@/auth';
import { env } from '@/env';

// Re-export types from the generated client
export type { CallRequest, CallResponse };

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
 * Create an outbound voice AI call
 */
export async function createOutboundCall(
  request: CallRequest,
): Promise<CallResponse> {
  const api = await createVoiceAIApi();

  const response = await api.createOutboundCallApiVoiceAiCallsPost(request);
  return response.data;
}

/**
 * Get call status by call ID
 */
export async function getCallStatus(callId: string): Promise<CallResponse> {
  const api = await createVoiceAIApi();

  const response = await api.getCallStatusApiVoiceAiCallsCallIdGet(callId);
  return response.data;
}

/**
 * React Query mutation hook for creating outbound calls
 */
export function useCreateOutboundCall(): UseMutationResult<CallResponse, Error, CallRequest> {
  return useMutation({
    mutationFn: createOutboundCall,
    onSuccess: (callResponse) => {
      console.log(`Voice AI call created: ${callResponse.call_id}`);
    },
    onError: (error) => {
      console.error('Failed to create voice AI call:', error);
    },
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
