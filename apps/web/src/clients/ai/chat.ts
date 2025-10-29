// Chat client - handles roofing chat API calls with streaming

import type { ChatMessage, ChatRequest } from '@maive/api/client';
import { getIdToken } from '@/auth';
import { env } from '@/env';

// Re-export types from the generated client
export type { ChatMessage, ChatRequest };

/**
 * Stream chat messages to the roofing chat endpoint
 * Returns a ReadableStream for SSE responses
 *
 * Note: We use fetch directly instead of the generated ChatApi client
 * because axios doesn't handle SSE streaming well. The endpoint and types
 * are still from the generated OpenAPI spec.
 */
export async function streamRoofingChat(
  messages: ChatMessage[],
): Promise<Response> {
  const token = await getIdToken();
  if (!token) throw new Error('Not authenticated');

  const chatRequest: ChatRequest = { messages };

  const response = await fetch(`${env.PUBLIC_SERVER_URL}/api/chat/roofing`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    credentials: 'include',
    body: JSON.stringify(chatRequest),
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.statusText}`);
  }

  return response;
}
