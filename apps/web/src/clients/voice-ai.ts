// Voice AI client - using generated API client

import {
  Configuration,
  VoiceAIApi,
  type CallRequest,
  type CallResponse,
} from '@maive/api-serverless/client';
import { useMutation, type UseMutationResult } from '@tanstack/react-query';

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
    }),
  );
};

/**
 * Create an outbound voice AI call with customer context
 */
export async function createOutboundCall(
  request: CallRequest,
): Promise<CallResponse> {
  const api = await createVoiceAIApi();

  const response = await api.createOutboundCall(request);
  return response.data;
}

/**
 * React Query mutation hook for creating outbound calls
 * Customer data will automatically update via 30-second polling
 */
export function useCreateOutboundCall(): UseMutationResult<CallResponse, Error, CallRequest> {
  return useMutation({
    mutationFn: createOutboundCall,
    onSuccess: (callResponse) => {
      console.log(`Voice AI call created: ${callResponse.call_id}`);
      // Customer data will update automatically via polling - no manual invalidation needed
    },
    onError: (error) => {
      console.error('Failed to create voice AI call:', error);
    },
  });
}
