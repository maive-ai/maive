// CRM client - using generated API client

import {
  CRMApi,
  Configuration,
  type ProjectList,
  type SrcIntegrationsCrmSchemasProject2 as Project,
} from '@maive/api/client';
import { useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query';

import { getIdToken } from '@/auth';
import { env } from '@/env';

// Re-export types from the generated client
export type { Project, ProjectList };

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
 * Fetch all projects from CRM using universal interface
 */
export async function fetchAllProjects(page: number = 1, pageSize: number = 50): Promise<ProjectList> {
  const api = await createCRMApi();

  const response = await api.getAllProjectsApiCrmProjectsGet(page, pageSize);
  console.log(
    `[CRM Client] Fetched ${response.data.total_count} projects (page ${page})`
  );
  return response.data;
}

/**
 * Fetch a single project by ID using universal interface
 */
export async function fetchProject(projectId: string): Promise<Project> {
  const api = await createCRMApi();
  const response = await api.getProjectApiCrmProjectsProjectIdGet(projectId);
  console.log(
    `[CRM Client] Fetched project ${projectId} - Status: ${response.data.status}`
  );
  return response.data;
}

/**
 * React Query hook for fetching all projects
 * Polls every 30 seconds to keep data fresh
 */
export function useFetchProjects(): UseQueryResult<ProjectList, Error> {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => fetchAllProjects(),
    staleTime: 30 * 1000, // Data is fresh for 30 seconds
    refetchInterval: 30 * 1000, // Poll every 30 seconds
    refetchIntervalInBackground: true,
  });
}

/**
 * React Query hook for fetching a single project
 * Polls every 30 seconds to keep data fresh
 */
export function useFetchProject(projectId: string): UseQueryResult<Project, Error> {
  return useQuery({
    queryKey: ['project', projectId],
    queryFn: () => fetchProject(projectId),
    staleTime: 30 * 1000, // Data is fresh for 30 seconds
    refetchInterval: 30 * 1000, // Poll every 30 seconds
    refetchIntervalInBackground: true,
    enabled: !!projectId, // Only run if projectId is provided
  });
}
