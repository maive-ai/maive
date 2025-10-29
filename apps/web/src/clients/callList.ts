// Call List client - using generated API client

import {
  CallListApi,
  Configuration,
  type AddToCallListRequest,
  type CallListItemResponse,
  type CallListResponse,
  type MarkCallCompletedRequest,
} from '@maive/api/client';
import { useMutation, useQuery, useQueryClient, type UseQueryResult, type UseMutationResult } from '@tanstack/react-query';

import { getIdToken } from '@/auth';
import { env } from '@/env';

// Re-export types from the generated client
export type { AddToCallListRequest, CallListItemResponse, CallListResponse, MarkCallCompletedRequest };

/**
 * Create a configured Call List API instance
 */
const createCallListApi = async (): Promise<CallListApi> => {
  const token = await getIdToken();
  if (!token) throw new Error('Not authenticated');

  return new CallListApi(
    new Configuration({
      accessToken: token,
      basePath: env.PUBLIC_SERVER_URL,
      baseOptions: { withCredentials: true },
    }),
  );
};

/**
 * Fetch the user's call list
 */
export async function fetchCallList(): Promise<CallListResponse> {
  const api = await createCallListApi();
  const response = await api.getCallListApiCallListGet();
  console.log(
    `[Call List Client] Fetched call list with ${response.data.total} items`
  );
  return response.data;
}

/**
 * Add projects to the call list
 */
export async function addToCallList(projectIds: string[]): Promise<CallListResponse> {
  const api = await createCallListApi();
  const response = await api.addToCallListApiCallListAddPost({ project_ids: projectIds });
  console.log(
    `[Call List Client] Added ${projectIds.length} projects to call list`
  );
  return response.data;
}

/**
 * Remove a project from the call list
 */
export async function removeFromCallList(projectId: string): Promise<void> {
  const api = await createCallListApi();
  await api.removeFromCallListApiCallListProjectIdDelete(projectId);
  console.log(
    `[Call List Client] Removed project ${projectId} from call list`
  );
}

/**
 * Clear all items from the call list
 */
export async function clearCallList(): Promise<void> {
  const api = await createCallListApi();
  await api.clearCallListApiCallListDelete();
  console.log(`[Call List Client] Cleared call list`);
}

/**
 * Mark a call as completed or not completed
 */
export async function markCallCompleted(
  projectId: string,
  completed: boolean = true
): Promise<CallListItemResponse> {
  const api = await createCallListApi();
  const response = await api.markCallCompletedApiCallListProjectIdCompletedPatch(
    projectId,
    { completed }
  );
  console.log(
    `[Call List Client] Marked project ${projectId} as ${completed ? 'completed' : 'not completed'}`
  );
  return response.data;
}

/**
 * React Query hook for fetching the call list
 */
export function useCallList(): UseQueryResult<CallListResponse, Error> {
  return useQuery({
    queryKey: ['callList'],
    queryFn: () => fetchCallList(),
    staleTime: 10 * 1000, // Data is fresh for 10 seconds
  });
}

/**
 * React Query mutation for adding projects to call list
 */
export function useAddToCallList(): UseMutationResult<CallListResponse, Error, string[]> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectIds: string[]) => addToCallList(projectIds),
    onSuccess: () => {
      // Invalidate call list query to refetch
      queryClient.invalidateQueries({ queryKey: ['callList'] });
    },
  });
}

/**
 * React Query mutation for removing a project from call list
 */
export function useRemoveFromCallList(): UseMutationResult<void, Error, string> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) => removeFromCallList(projectId),
    onSuccess: () => {
      // Invalidate call list query to refetch
      queryClient.invalidateQueries({ queryKey: ['callList'] });
    },
  });
}

/**
 * React Query mutation for clearing the call list
 */
export function useClearCallList(): UseMutationResult<void, Error, void> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => clearCallList(),
    onSuccess: () => {
      // Invalidate call list query to refetch
      queryClient.invalidateQueries({ queryKey: ['callList'] });
    },
  });
}

/**
 * React Query mutation for marking a call as completed
 */
export function useMarkCallCompleted(): UseMutationResult<
  CallListItemResponse,
  Error,
  { projectId: string; completed?: boolean }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, completed = true }) => markCallCompleted(projectId, completed),
    onSuccess: () => {
      // Invalidate call list query to refetch
      queryClient.invalidateQueries({ queryKey: ['callList'] });
    },
  });
}
