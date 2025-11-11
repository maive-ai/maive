import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
} from '@assistant-ui/react';
import { Thread } from './Thread';
import { chatHistoryAdapter } from './chatHistoryAdapter';
import { FileSearchToolUI } from './tool-ui/FileSearchToolUI';
import { McpToolUI } from './tool-ui/McpToolUI';
import { ReasoningToolUI } from './tool-ui/ReasoningToolUI';
import { WebSearchToolUI } from './tool-ui/WebSearchToolUI';
import { streamRoofingChat } from '@/clients/ai/chat';

interface Citation {
  url: string;
  title?: string | null;
  snippet?: string | null;
  accessed_at?: string | null;
}

interface ReasoningSummaryEvent {
  id: string;
  summary: string;
}

const chatAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal }) {
    // Convert assistant-ui messages to our API format
    const apiMessages = messages.map((m) => ({
      role: m.role,
      content:
        m.content
          .filter((c) => c.type === 'text')
          .map((c) => (c.type === 'text' ? c.text : ''))
          .join('\n') || '',
    }));

    try {
      const response = await streamRoofingChat(apiMessages);

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedText = '';
      const citations: Citation[] = [];
      const toolCalls: Map<string, any> = new Map();
      let reasoningSummary: ReasoningSummaryEvent | null = null;
      let currentEventType = 'message';
      let currentActiveToolCallId: string | null = null; // Track the currently active tool

      while (true) {
        if (abortSignal?.aborted) {
          reader.cancel();
          break;
        }

        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          // Parse SSE event type
          if (line.startsWith('event: ')) {
            currentEventType = line.slice(7);
            continue;
          }

          // Parse SSE data
          if (line.startsWith('data: ')) {
            const data = line.slice(6);

            // Handle different event types
            if (currentEventType === 'done') {
              // Stream complete - append citations as formatted text
              let finalText = accumulatedText;

              // Add citations as formatted markdown/text at the end
              if (citations.length > 0) {
                const citationsText = citations
                  .map((citation, index) => {
                    const title = citation.title || citation.url;
                    const snippet = citation.snippet ? `\n${citation.snippet}` : '';
                    return `[${index + 1}] [${title}](${citation.url})${snippet}`;
                  })
                  .join('\n\n');

                finalText += `\n\n---\n\n**Sources:**\n\n${citationsText}`;
              }

              // Build content array with text and tool calls
              const content: any[] = [];

              if (finalText) {
                content.push({ type: 'text', text: finalText });
              }

              // Add tool calls to content
              toolCalls.forEach((toolCall) => {
                content.push({
                  type: 'tool-call',
                  toolCallId: toolCall.tool_call_id,
                  toolName: toolCall.tool_name,
                  args: toolCall.args,
                  result: toolCall.result,
                });
              });

              yield { content };
              return;
            } else if (currentEventType === 'tool_call') {
              // Parse tool call event
              try {
                const toolCall = JSON.parse(data);
                const existingToolCall = toolCalls.get(toolCall.tool_call_id);

                // If this is a new tool call starting (InProgress event)
                if (!existingToolCall && !toolCall.result) {
                  // This is a new tool starting - update the active tool
                  currentActiveToolCallId = toolCall.tool_call_id;

                  // Mark all previous tools as complete
                  toolCalls.forEach((tc) => {
                    tc.result = { status: 'complete' };
                  });
                }

                // Store the tool call
                toolCalls.set(toolCall.tool_call_id, toolCall);

                // Build content - only show the currently active tool
                // Hide reasoning summary when a tool call is active
                const content: any[] = [];

                if (currentActiveToolCallId) {
                  const activeTool = toolCalls.get(currentActiveToolCallId);
                  if (activeTool) {
                    // Always show active tool without result (keeps shimmer visible)
                    content.push({
                      type: 'tool-call',
                      toolCallId: activeTool.tool_call_id,
                      toolName: activeTool.tool_name,
                      args: activeTool.args,
                      result: null, // Always null to keep shimmer showing
                    });
                  }
                } else if (reasoningSummary && !accumulatedText) {
                  // Show reasoning summary if no active tool and no text yet
                  content.push({
                    type: 'tool-call',
                    toolCallId: reasoningSummary.id,
                    toolName: 'reasoning',
                    args: {
                      summary: reasoningSummary.summary,
                    },
                    result: null,
                  });
                }

                if (content.length > 0) {
                  yield { content };
                }
              } catch (e) {
                console.error('Failed to parse tool call:', e);
              }
            } else if (currentEventType === 'citation') {
              // Parse and store citation
              try {
                const citation: Citation = JSON.parse(data);
                citations.push(citation);
              } catch (e) {
                console.error('Failed to parse citation:', e);
              }
            } else if (currentEventType === 'error') {
              throw new Error(data);
            } else if (currentEventType === 'reasoning_summary') {
              try {
                const summary: ReasoningSummaryEvent = JSON.parse(data);
                reasoningSummary = summary;

                // Clear active tool - reasoning summary replaces tool display
                currentActiveToolCallId = null;

                // Mark all tool calls as complete
                toolCalls.forEach((tc) => {
                  tc.result = { status: 'complete' };
                });

                // Build content with just reasoning summary (no tools, no text)
                const content: any[] = [];
                
                if (reasoningSummary && !accumulatedText) {
                  content.push({
                    type: 'tool-call',
                    toolCallId: reasoningSummary.id,
                    toolName: 'reasoning',
                    args: {
                      summary: reasoningSummary.summary,
                    },
                    result: null,
                  });
                }

                if (content.length > 0) {
                  yield { content };
                }
              } catch (e) {
                console.error('Failed to parse reasoning summary:', e);
              }
            } else if (currentEventType === 'heartbeat') {
              // SSE keepalive to prevent HTTP/2 timeout - ignore
              continue;
            } else {
              // Regular message content
              const unescapedData = data.replace(/\\n/g, '\n');
              accumulatedText += unescapedData;

              // Clear active tool and reasoning summary when text arrives
              currentActiveToolCallId = null;
              reasoningSummary = null;

              // Mark all tool calls as complete when text arrives
              toolCalls.forEach((tc) => {
                if (!tc.result) {
                  tc.result = { status: 'complete' };
                }
              });

              // Build content array with text and tool calls
              const content: any[] = [];

              if (accumulatedText) {
                content.push({ type: 'text', text: accumulatedText });
              }

              // Add all completed tool calls to content
              toolCalls.forEach((toolCall) => {
                content.push({
                  type: 'tool-call',
                  toolCallId: toolCall.tool_call_id,
                  toolName: toolCall.tool_name,
                  args: toolCall.args,
                  result: toolCall.result,
                });
              });

              if (content.length > 0) {
                yield { content };
              }
            }

            // Reset to default event type
            currentEventType = 'message';
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }
      throw error;
    }
  },
};

export function ChatRuntimeProvider() {
  const runtime = useLocalRuntime(chatAdapter, {
    adapters: { history: chatHistoryAdapter },
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <WebSearchToolUI />
      <FileSearchToolUI />
      <McpToolUI />
      <ReasoningToolUI />
      <div className="h-full">
        <Thread />
      </div>
    </AssistantRuntimeProvider>
  );
}
