// Workflows client - orchestrates voice AI calls with monitoring and CRM integration

import {
  Configuration,
  WorkflowsApi,
  type CallRequest,
  type CallResponse,
} from '@maive/api/client';
import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';

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
export async function callAndWriteToCrm(
  request: CallRequest,
): Promise<CallResponse> {
  const api = await createWorkflowsApi();

  const response = await api.callAndWriteResultsToCrmApiWorkflowsCallAndWriteResultsToCrmPost(request);
  return response.data;
}


/**
 * React Query mutation hook for creating outbound calls
 * @param projectId - Optional project ID to invalidate queries after call completes
 */
export function useCallAndWriteToCrm(projectId?: string): UseMutationResult<CallResponse, Error, CallRequest> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: callAndWriteToCrm,
    onSuccess: async (callResponse) => {
      // Invalidate active call query to restart polling
      await queryClient.invalidateQueries({ queryKey: ['active-call'] });

      // Invalidate project queries to refetch updated status
      if (projectId) {
        await queryClient.invalidateQueries({ queryKey: ['project-status', projectId] });
      }
      await queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
    onError: (error) => {
      console.error('[Workflows] Failed to create voice AI call:', error);
    },
  });
}

