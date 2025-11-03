import { streamRoofingChat } from '@/clients/ai/chat';
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
} from '@assistant-ui/react';
import { Thread } from './Thread';
import { FileSearchToolUI } from './tool-ui/FileSearchToolUI';
import { ReasoningToolUI } from './tool-ui/ReasoningToolUI';
import { WebSearchToolUI } from './tool-ui/WebSearchToolUI';

interface Citation {
  url: string;
  title?: string | null;
  snippet?: string | null;
  accessed_at?: string | null;
}

interface ToolCallEvent {
  tool_call_id: string;
  tool_name: string;
  args: Record<string, unknown>;
  result: Record<string, unknown> | null;
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
      const toolCalls: Map<string, ToolCallEvent> = new Map();
      let reasoningSummary: ReasoningSummaryEvent | null = null;
      let currentEventType = 'message';

      const buildContent = (text: string, hideReasoning: boolean = false) => {
        const content: any[] = [];

        if (text) {
          content.push({ type: 'text', text });
        }

        // Only show reasoning summary if:
        // 1. We have a reasoning summary
        // 2. There's no text content yet (reasoning happens before text)
        // 3. We haven't explicitly hidden it (hideReasoning flag)
        if (reasoningSummary && !text && !hideReasoning) {
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

        // Always show tool calls when present
        toolCalls.forEach((toolCall) => {
          content.push({
            type: 'tool-call',
            toolCallId: toolCall.tool_call_id,
            toolName: toolCall.tool_name,
            args: toolCall.args,
            result: toolCall.result ?? null,
          });
        });

        return content;
      };

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

              toolCalls.forEach((toolCall, key) => {
                if (!toolCall.result) {
                  toolCalls.set(key, { ...toolCall, result: { status: 'complete' } });
                }
              });

              // Clear reasoning summary when stream is done
              reasoningSummary = null;

              const content = buildContent(finalText);
              if (content.length > 0) {
                yield { content };
              }
              return;
            }

            if (currentEventType === 'tool_call') {
              try {
                const toolCall: ToolCallEvent = JSON.parse(data);
                toolCalls.set(toolCall.tool_call_id, {
                  ...toolCall,
                  result: toolCall.result ?? null,
                });

                // Hide reasoning summary when tool calls appear
                const content = buildContent(accumulatedText, true);
                if (content.length > 0) {
                  yield { content };
                }
              } catch (e) {
                console.error('Failed to parse tool call:', e);
              }
            } else if (currentEventType === 'reasoning_summary') {
              try {
                const summary: ReasoningSummaryEvent = JSON.parse(data);
                reasoningSummary = summary;

                const content = buildContent(accumulatedText);
                if (content.length > 0) {
                  yield { content };
                }
              } catch (e) {
                console.error('Failed to parse reasoning summary:', e);
              }
            } else if (currentEventType === 'citation') {
              try {
                const citation: Citation = JSON.parse(data);
                citations.push(citation);
              } catch (e) {
                console.error('Failed to parse citation:', e);
              }
            } else if (currentEventType === 'error') {
              throw new Error(data);
            } else {
              const unescapedData = data.replace(/\\n/g, '\n');
              accumulatedText += unescapedData;

              // Clear reasoning summary when text starts streaming
              reasoningSummary = null;

              toolCalls.forEach((toolCall, key) => {
                if (!toolCall.result) {
                  toolCalls.set(key, { ...toolCall, result: { status: 'complete' } });
                }
              });

              const content = buildContent(accumulatedText);
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
  const runtime = useLocalRuntime(chatAdapter);

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <WebSearchToolUI />
      <FileSearchToolUI />
      <ReasoningToolUI />
      <div className="h-full">
        <Thread />
      </div>
    </AssistantRuntimeProvider>
  );
}
