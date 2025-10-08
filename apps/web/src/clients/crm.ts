// CRM client - using generated API client

import {
  CRMApi,
  Configuration,
  type ProjectData,
  type ProjectStatusListResponse,
  type ProjectStatusResponse,
} from '@maive/api/client';
import { useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query';

import { getIdToken } from '@/auth';
import { env } from '@/env';

// Re-export types from the generated client
export type { ProjectData, ProjectStatusListResponse, ProjectStatusResponse };

/**
 * Create a configured CRM API instance
 */
const createCRMApi = async (): Promise<CRMApi> => {
  const token = await getIdToken();
  if (!token) throw new Error('Not authenticated');

  return new CRMApi(
    new Configuration({
      accessToken: token,
      basePath: env.PUBLIC_SERVER_URL,
      baseOptions: { withCredentials: true },
    }),
  );
};

/**
 * Fetch all projects from CRM
 */
export async function fetchAllProjects(): Promise<ProjectStatusListResponse> {
  const api = await createCRMApi();

  const response = await api.getAllProjectStatusesApiCrmProjectsStatusGet();
  return response.data;
}

/**
 * Fetch a single project status by ID
 */
export async function fetchProjectStatus(projectId: string): Promise<ProjectStatusResponse> {
  const api = await createCRMApi();
  const response = await api.getProjectStatusApiCrmProjectsProjectIdStatusGet(projectId);
  return response.data;
}

/**
 * React Query hook for fetching all projects
 * Polls every 30 seconds to keep data fresh
 */
export function useFetchProjects(): UseQueryResult<ProjectStatusListResponse, Error> {
  return useQuery({
    queryKey: ['projects'],
    queryFn: fetchAllProjects,
    staleTime: 30 * 1000, // Data is fresh for 30 seconds
    refetchInterval: 30 * 1000, // Poll every 30 seconds
    refetchIntervalInBackground: true,
  });
}

/**
 * React Query hook for fetching a single project status
 * Polls every 30 seconds to keep data fresh
 */
export function useFetchProject(projectId: string): UseQueryResult<ProjectStatusResponse, Error> {
  return useQuery({
    queryKey: ['project-status', projectId],
    queryFn: () => fetchProjectStatus(projectId),
    staleTime: 30 * 1000, // Data is fresh for 30 seconds
    refetchInterval: 30 * 1000, // Poll every 30 seconds
    refetchIntervalInBackground: true,
    enabled: !!projectId, // Only run if projectId is provided
  });
}

/**
 * Create a new project in the CRM (Mock CRM only)
 */
export async function createProject(projectData: ProjectData): Promise<void> {
  const api = await createCRMApi();
  await api.createProjectApiCrmProjectsPost(projectData);
}

/**
 * React Query mutation hook for creating a new project
 * Invalidates projects query on success to refresh the list
 */
export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      // Invalidate projects query to refetch the list
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}
