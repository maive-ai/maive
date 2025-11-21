// CRM client - using generated API client

import {
  CRMApi,
  Configuration,
  type MockNote,
  type MockProject,
  type Project,
  type ProjectList,
} from '@maive/api/client';
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query';

import { env } from '@/env';
import { baseClient } from './base';

// Re-export types from the generated client
export type { MockNote, MockProject, Project, ProjectList };

/**
 * Create a configured CRM API instance using the shared axios client
 */
const createCRMApi = (): CRMApi => {
  return new CRMApi(
    new Configuration({
      basePath: env.PUBLIC_SERVER_URL,
    }),
    undefined,
    baseClient,
  );
};

/**
 * Fetch all projects from CRM using universal interface
 */
export async function fetchAllProjects(
  page: number = 1,
  pageSize: number = 50,
  search?: string | null,
): Promise<ProjectList> {
  const api = createCRMApi();

  // Use baseClient directly to add search parameter until API client is regenerated
  if (search) {
    const response = await baseClient.get<ProjectList>('/api/crm/projects', {
      params: {
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
      },
    });
    console.log(
      `[CRM Client] Fetched ${response.data.total_count} projects (page ${page}, search: "${search}")`,
    );
    return response.data;
  }

  // Use generated client when no search parameter
  const response = await api.getAllProjectsApiCrmProjectsGet(page, pageSize);
  console.log(
    `[CRM Client] Fetched ${response.data.total_count} projects (page ${page})`,
  );
  return response.data;
}

/**
 * Fetch a single project by ID using universal interface
 */
export async function fetchProject(projectId: string): Promise<Project> {
  const api = createCRMApi();
  const response = await api.getProjectApiCrmProjectsProjectIdGet(projectId);
  console.log(
    `[CRM Client] Fetched project ${projectId} - Status: ${response.data.status}`,
  );
  return response.data;
}

/**
 * React Query hook for fetching all projects
 * Polls every 30 seconds to keep data fresh
 */
export function useFetchProjects(
  page: number = 1,
  pageSize: number = 50,
  search?: string | null,
): UseQueryResult<ProjectList, Error> {
  return useQuery({
    queryKey: ['projects', page, pageSize, search],
    queryFn: () => fetchAllProjects(page, pageSize, search),
    staleTime: 30 * 1000, // Data is fresh for 30 seconds
    refetchInterval: 30 * 1000, // Poll every 30 seconds
    refetchIntervalInBackground: true,
  });
}

/**
 * React Query hook for fetching a single project
 * Polls every 30 seconds to keep data fresh
 */
export function useFetchProject(
  projectId: string,
): UseQueryResult<Project, Error> {
  return useQuery({
    queryKey: ['project', projectId],
    queryFn: () => fetchProject(projectId),
    staleTime: 30 * 1000, // Data is fresh for 30 seconds
    refetchInterval: 30 * 1000, // Poll every 30 seconds
    refetchIntervalInBackground: true,
    enabled: !!projectId, // Only run if projectId is provided
  });
}

/**
 * File metadata interface
 */
export interface FileMetadata {
  id: string;
  filename: string;
  content_type: string;
  size: number;
  record_type_name: string;
  description?: string;
  date_created: number;
  created_by_name: string;
  is_private: boolean;
}

/**
 * Fetch all files for a specific job/project
 */
export async function fetchJobFiles(jobId: string): Promise<FileMetadata[]> {
  const api = createCRMApi();
  const response = await api.getJobFilesApiCrmJobsJobIdFilesGet(jobId);
  return response.data as FileMetadata[];
}

/**
 * Download a specific file with authentication
 */
export async function downloadFile(
  fileId: string,
  filename?: string,
  contentType?: string,
): Promise<void> {
  const api = createCRMApi();

  const response = await api.downloadFileApiCrmFilesFileIdDownloadGet(
    fileId,
    filename || null,
    contentType || null,
    { responseType: 'blob' },
  );

  // Trigger browser download
  const blob = new Blob([response.data], {
    type: contentType || 'application/octet-stream',
  });
  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = filename || `download_${fileId}`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(downloadUrl);
}

/**
 * React Query hook for fetching job files
 */
export function useFetchJobFiles(
  jobId: string,
): UseQueryResult<FileMetadata[], Error> {
  return useQuery({
    queryKey: ['job-files', jobId],
    queryFn: () => fetchJobFiles(jobId),
    staleTime: 60 * 1000, // Data is fresh for 60 seconds
    enabled: !!jobId, // Only run if jobId is provided
  });
}

/**
 * Create a mock project (Mock CRM only)
 */
export async function createMockProject(
  projectData: MockProject,
): Promise<Project> {
  const api = createCRMApi();
  const response = await api.createMockProjectApiCrmProjectsPost(projectData);
  console.log(
    `[CRM Client] Created mock project: ${response.data.customer_name}`,
  );
  return response.data;
}

/**
 * React Query mutation for creating a mock project
 */
export function useCreateMockProject(): UseMutationResult<
  Project,
  Error,
  MockProject
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createMockProject,
    onSuccess: () => {
      // Invalidate projects query to refetch
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

/**
 * Update a mock project (Mock CRM only)
 */
export async function updateMockProject(
  projectId: string,
  projectData: MockProject,
): Promise<Project> {
  const api = createCRMApi();
  const response = await api.updateMockProjectApiCrmProjectsProjectIdPatch(
    projectId,
    projectData,
  );
  console.log(
    `[CRM Client] Updated mock project: ${response.data.customer_name}`,
  );
  return response.data;
}

/**
 * React Query mutation for updating a mock project
 */
export function useUpdateMockProject(): UseMutationResult<
  Project,
  Error,
  { projectId: string; projectData: MockProject }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, projectData }) =>
      updateMockProject(projectId, projectData),
    onSuccess: (_data, variables) => {
      // Invalidate both the projects list and the specific project
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.invalidateQueries({
        queryKey: ['project', variables.projectId],
      });
    },
  });
}
