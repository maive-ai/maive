// Scheduled Groups client - using generated API client

import {
  ScheduledGroupsApi,
  Configuration,
  type CreateScheduledGroupRequest,
  type UpdateScheduledGroupRequest,
  type ScheduledGroupResponse,
  type ScheduledGroupDetailResponse,
  type ScheduledGroupsListResponse,
  type ScheduledGroupMemberResponse,
  type AddProjectsToGroupRequest,
  type UpdateGroupStatusRequest,
  type GoalType,
  type WhoToCall,
} from '@maive/api/client';
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from '@tanstack/react-query';

import { apiClient } from '@/lib/apiClient';
import { env } from '@/env';

// Re-export types from the generated client
export type {
  CreateScheduledGroupRequest,
  UpdateScheduledGroupRequest,
  ScheduledGroupResponse,
  ScheduledGroupDetailResponse,
  ScheduledGroupsListResponse,
  ScheduledGroupMemberResponse,
  AddProjectsToGroupRequest,
  UpdateGroupStatusRequest,
  GoalType,
  WhoToCall,
};

/**
 * Create a configured Scheduled Groups API instance using the shared axios client
 */
const createScheduledGroupsApi = (): ScheduledGroupsApi => {
  return new ScheduledGroupsApi(
    new Configuration({
      basePath: env.PUBLIC_SERVER_URL,
    }),
    undefined,
    apiClient
  );
};

/**
 * Create a new scheduled group
 */
export async function createScheduledGroup(
  request: CreateScheduledGroupRequest
): Promise<ScheduledGroupResponse> {
  const api = createScheduledGroupsApi();
  const response = await api.createScheduledGroupApiScheduledGroupsPost(request);
  console.log(`[Scheduled Groups Client] Created group: ${response.data.name}`);
  return response.data;
}

/**
 * List all scheduled groups for the user
 */
export async function fetchScheduledGroups(): Promise<ScheduledGroupsListResponse> {
  const api = createScheduledGroupsApi();
  const response = await api.listScheduledGroupsApiScheduledGroupsGet();
  console.log(`[Scheduled Groups Client] Fetched ${response.data.total} groups`);
  return response.data;
}

/**
 * Get a scheduled group with its members
 */
export async function fetchScheduledGroupDetail(
  groupId: number
): Promise<ScheduledGroupDetailResponse> {
  const api = createScheduledGroupsApi();
  const response = await api.getScheduledGroupApiScheduledGroupsGroupIdGet(groupId);
  console.log(
    `[Scheduled Groups Client] Fetched group ${groupId} with ${response.data.members.length} members`
  );
  return response.data;
}

/**
 * Update a scheduled group
 */
export async function updateScheduledGroup(
  groupId: number,
  request: UpdateScheduledGroupRequest
): Promise<ScheduledGroupResponse> {
  const api = createScheduledGroupsApi();
  const response = await api.updateScheduledGroupApiScheduledGroupsGroupIdPut(
    groupId,
    request
  );
  console.log(`[Scheduled Groups Client] Updated group ${groupId}`);
  return response.data;
}

/**
 * Delete a scheduled group
 */
export async function deleteScheduledGroup(groupId: number): Promise<void> {
  const api = createScheduledGroupsApi();
  await api.deleteScheduledGroupApiScheduledGroupsGroupIdDelete(groupId);
  console.log(`[Scheduled Groups Client] Deleted group ${groupId}`);
}

/**
 * Toggle group active status
 */
export async function toggleGroupActive(
  groupId: number,
  isActive: boolean
): Promise<ScheduledGroupResponse> {
  const api = createScheduledGroupsApi();
  const request: UpdateGroupStatusRequest = { is_active: isActive };
  const response = await api.toggleGroupActiveApiScheduledGroupsGroupIdActivePatch(
    groupId,
    request
  );
  console.log(`[Scheduled Groups Client] Toggled group ${groupId} active: ${isActive}`);
  return response.data;
}

/**
 * Add projects to a group
 */
export async function addProjectsToGroup(
  groupId: number,
  projectIds: string[]
): Promise<ScheduledGroupDetailResponse> {
  const api = createScheduledGroupsApi();
  const request: AddProjectsToGroupRequest = { project_ids: projectIds };
  const response = await api.addProjectsToGroupApiScheduledGroupsGroupIdMembersPost(
    groupId,
    request
  );
  console.log(
    `[Scheduled Groups Client] Added ${projectIds.length} projects to group ${groupId}`
  );
  return response.data;
}

/**
 * Remove a project from a group
 */
export async function removeProjectFromGroup(
  groupId: number,
  projectId: string
): Promise<void> {
  const api = createScheduledGroupsApi();
  await api.removeProjectFromGroupApiScheduledGroupsGroupIdMembersProjectIdDelete(
    groupId,
    projectId
  );
  console.log(`[Scheduled Groups Client] Removed project ${projectId} from group ${groupId}`);
}

/**
 * Mark goal as completed for a project
 */
export async function markGoalCompleted(
  groupId: number,
  projectId: string,
  completed: boolean = true
): Promise<ScheduledGroupMemberResponse> {
  const api = createScheduledGroupsApi();
  const response =
    await api.markGoalCompletedApiScheduledGroupsGroupIdMembersProjectIdCompletedPatch(
      groupId,
      projectId,
      completed
    );
  console.log(
    `[Scheduled Groups Client] Marked goal ${completed ? 'completed' : 'not completed'} for project ${projectId}`
  );
  return response.data;
}

/**
 * React Query hook for fetching scheduled groups
 */
export function useScheduledGroups(): UseQueryResult<ScheduledGroupsListResponse, Error> {
  return useQuery({
    queryKey: ['scheduledGroups'],
    queryFn: () => fetchScheduledGroups(),
    staleTime: 10 * 1000, // Data is fresh for 10 seconds
  });
}

/**
 * React Query hook for fetching a single scheduled group detail
 */
export function useScheduledGroupDetail(
  groupId: number | null
): UseQueryResult<ScheduledGroupDetailResponse, Error> {
  return useQuery({
    queryKey: ['scheduledGroup', groupId],
    queryFn: () => fetchScheduledGroupDetail(groupId!),
    enabled: groupId !== null,
    staleTime: 10 * 1000,
  });
}

/**
 * React Query mutation for creating a scheduled group
 */
export function useCreateScheduledGroup(): UseMutationResult<
  ScheduledGroupResponse,
  Error,
  CreateScheduledGroupRequest
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateScheduledGroupRequest) => createScheduledGroup(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduledGroups'] });
    },
  });
}

/**
 * React Query mutation for updating a scheduled group
 */
export function useUpdateScheduledGroup(): UseMutationResult<
  ScheduledGroupResponse,
  Error,
  { groupId: number; request: UpdateScheduledGroupRequest }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ groupId, request }) => updateScheduledGroup(groupId, request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['scheduledGroups'] });
      queryClient.invalidateQueries({ queryKey: ['scheduledGroup', variables.groupId] });
    },
  });
}

/**
 * React Query mutation for deleting a scheduled group
 */
export function useDeleteScheduledGroup(): UseMutationResult<void, Error, number> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (groupId: number) => deleteScheduledGroup(groupId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduledGroups'] });
    },
  });
}

/**
 * React Query mutation for toggling group active status
 */
export function useToggleGroupActive(): UseMutationResult<
  ScheduledGroupResponse,
  Error,
  { groupId: number; isActive: boolean }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ groupId, isActive }) => toggleGroupActive(groupId, isActive),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['scheduledGroups'] });
      queryClient.invalidateQueries({ queryKey: ['scheduledGroup', variables.groupId] });
    },
  });
}

/**
 * React Query mutation for adding projects to a group
 */
export function useAddProjectsToGroup(): UseMutationResult<
  ScheduledGroupDetailResponse,
  Error,
  { groupId: number; projectIds: string[] }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ groupId, projectIds }) => addProjectsToGroup(groupId, projectIds),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['scheduledGroups'] });
      queryClient.invalidateQueries({ queryKey: ['scheduledGroup', variables.groupId] });
    },
  });
}

/**
 * React Query mutation for removing a project from a group
 */
export function useRemoveProjectFromGroup(): UseMutationResult<
  void,
  Error,
  { groupId: number; projectId: string }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ groupId, projectId }) => removeProjectFromGroup(groupId, projectId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['scheduledGroups'] });
      queryClient.invalidateQueries({ queryKey: ['scheduledGroup', variables.groupId] });
    },
  });
}

/**
 * React Query mutation for marking goal completed
 */
export function useMarkGoalCompleted(): UseMutationResult<
  ScheduledGroupMemberResponse,
  Error,
  { groupId: number; projectId: string; completed: boolean }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ groupId, projectId, completed }) =>
      markGoalCompleted(groupId, projectId, completed),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['scheduledGroups'] });
      queryClient.invalidateQueries({ queryKey: ['scheduledGroup', variables.groupId] });
    },
  });
}
