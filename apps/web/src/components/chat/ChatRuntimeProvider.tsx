import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
} from '@assistant-ui/react';
import { Thread } from './Thread';
import { streamRoofingChat } from '@/clients/ai/chat';
import { WebSearchToolUI } from './tool-ui/WebSearchToolUI';
import { FileSearchToolUI } from './tool-ui/FileSearchToolUI';
import { ShimmerText } from '@/components/ui/shimmer-text';

interface Citation {
  url: string;
  title?: string | null;
  snippet?: string | null;
  accessed_at?: string | null;
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
      let currentEventType = 'message';

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
                toolCalls.set(toolCall.tool_call_id, toolCall);

                // Yield current state with accumulated text and tool calls
                const content: any[] = [];

                if (accumulatedText) {
                  content.push({ type: 'text', text: accumulatedText });
                }

                // Add all tool calls to content
                toolCalls.forEach((tc) => {
                  content.push({
                    type: 'tool-call',
                    toolCallId: tc.tool_call_id,
                    toolName: tc.tool_name,
                    args: tc.args,
                    result: tc.result,
                  });
                });

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
              // Skip reasoning summary for now
              // TODO: Display reasoning summary ephemerally
              continue;
            } else {
              // Regular message content
              const unescapedData = data.replace(/\\n/g, '\n');
              accumulatedText += unescapedData;

              // Build content array with text and tool calls
              const content: any[] = [];

              if (accumulatedText) {
                content.push({ type: 'text', text: accumulatedText });
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
      <div className="h-full">
        <Thread />
      </div>
    </AssistantRuntimeProvider>
  );
}
