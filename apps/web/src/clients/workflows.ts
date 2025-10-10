// Workflows client - orchestrates voice AI calls with monitoring and CRM integration

import {
  Configuration,
  WorkflowsApi,
  type CallRequest,
  type CallResponse,
} from '@maive/api/client';
import { useMutation, type UseMutationResult } from '@tanstack/react-query';

import { getIdToken } from '@/auth';
import { env } from '@/env';

// Re-export types from the generated client
export type { CallRequest, CallResponse };

/**
 * Create a configured Workflows API instance
 */
const createWorkflowsApi = async (): Promise<WorkflowsApi> => {
  const token = await getIdToken();
  if (!token) throw new Error('Not authenticated');

  return new WorkflowsApi(
    new Configuration({
      accessToken: token,
      basePath: env.PUBLIC_SERVER_URL,
      baseOptions: { withCredentials: true },
    }),
  );
};

/**
 * Create an outbound voice AI call with monitoring and CRM integration
 */
export async function createOutboundCall(
  request: CallRequest,
): Promise<CallResponse> {
  const api = await createWorkflowsApi();

  const response = await api.createMonitoredCallApiWorkflowsMonitoredCallPost(request);
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

