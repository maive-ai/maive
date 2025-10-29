import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
} from '@assistant-ui/react';
import { Thread } from './Thread';
import { streamRoofingChat } from '@/clients/ai/chat';

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

              yield {
                content: [{ type: 'text', text: finalText }],
              };
              return;
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
            } else {
              // Regular message content
              const unescapedData = data.replace(/\\n/g, '\n');
              accumulatedText += unescapedData;
              yield {
                content: [{ type: 'text', text: accumulatedText }],
              };
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
      <div className="h-full">
        <Thread />
      </div>
    </AssistantRuntimeProvider>
  );
}
