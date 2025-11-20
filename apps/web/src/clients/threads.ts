// Thread client - handles thread and message API calls

import {
  ThreadsApi,
  Configuration,
  type ThreadResponse,
  type ThreadListResponse,
  type MessageResponse,
  type MessageListResponse,
  type CreateThreadRequest,
  type UpdateThreadTitleRequest,
  type CreateMessageRequest,
  type GenerateTitleRequest,
} from '@maive/api/client';
import { getAccessToken } from '@/clients/auth';
import { baseClient } from '@/clients/base';
import { env } from '@/env';

// Re-export types
export type {
  ThreadResponse,
  ThreadListResponse,
  MessageResponse,
  MessageListResponse,
  CreateThreadRequest,
  UpdateThreadTitleRequest,
  CreateMessageRequest,
  GenerateTitleRequest,
};

/**
 * Create a configured Threads API instance using the shared axios client
 */
const createThreadsApi = (): ThreadsApi => {
  return new ThreadsApi(
    new Configuration({
      basePath: env.PUBLIC_SERVER_URL,
    }),
    undefined,
    baseClient,
  );
};

// ========== Thread Operations ==========

/**
 * Create a new thread
 */
export async function createThread(
  request: CreateThreadRequest,
): Promise<ThreadResponse> {
  const api = createThreadsApi();
  const response = await api.createThreadApiThreadsPost(request);
  return response.data;
}

/**
 * List all threads for the current user
 */
export async function listThreads(
  includeArchived = true,
): Promise<ThreadListResponse> {
  const api = createThreadsApi();
  const response = await api.listThreadsApiThreadsGet(includeArchived);
  return response.data;
}

/**
 * Get a specific thread by ID
 */
export async function getThread(threadId: string): Promise<ThreadResponse> {
  const api = createThreadsApi();
  const response = await api.getThreadApiThreadsThreadIdGet(threadId);
  return response.data;
}

/**
 * Update a thread's title
 */
export async function updateThreadTitle(
  threadId: string,
  request: UpdateThreadTitleRequest,
): Promise<ThreadResponse> {
  const api = createThreadsApi();
  const response = await api.updateThreadTitleApiThreadsThreadIdTitlePatch(threadId, request);
  return response.data;
}

/**
 * Archive a thread
 */
export async function archiveThread(threadId: string): Promise<ThreadResponse> {
  const api = createThreadsApi();
  const response = await api.archiveThreadApiThreadsThreadIdArchivePatch(threadId);
  return response.data;
}

/**
 * Unarchive a thread
 */
export async function unarchiveThread(
  threadId: string,
): Promise<ThreadResponse> {
  const api = createThreadsApi();
  const response = await api.unarchiveThreadApiThreadsThreadIdUnarchivePatch(threadId);
  return response.data;
}

/**
 * Delete a thread and all its messages
 */
export async function deleteThread(threadId: string): Promise<void> {
  const api = createThreadsApi();
  await api.deleteThreadApiThreadsThreadIdDelete(threadId);
}

/**
 * Generate a title for a thread using AI
 * Returns a ReadableStream for SSE responses
 */
export async function generateThreadTitle(
  threadId: string,
  request: GenerateTitleRequest,
): Promise<Response> {
  const token = await getAccessToken();
  if (!token) throw new Error('Not authenticated');

  const response = await fetch(
    `/api/threads/${threadId}/generate-title`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      credentials: 'include',
      body: JSON.stringify(request),
    },
  );

  if (!response.ok) {
    throw new Error(`Failed to generate title: ${response.statusText}`);
  }

  return response;
}

// ========== Message Operations ==========

/**
 * Get all messages for a thread
 */
export async function getMessages(
  threadId: string,
): Promise<MessageListResponse> {
  const api = createThreadsApi();
  const response = await api.getMessagesApiThreadsThreadIdMessagesGet(threadId);
  return response.data;
}

/**
 * Create a new message in a thread
 */
export async function createMessage(
  threadId: string,
  request: CreateMessageRequest,
): Promise<MessageResponse> {
  const api = createThreadsApi();
  const response = await api.createMessageApiThreadsThreadIdMessagesPost(threadId, request);
  return response.data;
}
