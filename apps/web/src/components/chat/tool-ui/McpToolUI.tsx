import { makeAssistantToolUI } from '@assistant-ui/react';
import ShinyText from '@/components/ShinyText';

export const McpToolUI = makeAssistantToolUI({
  toolName: 'mcp_tool',
  render: ({ args, result }) => {
    // Show shimmer while searching (no result yet)
    if (!result) {
      const description = (args as { description?: string })?.description || 'Searching CRM...';
      return (
        <div className="mb-2">
          <ShinyText text={description} className="text-base leading-7 text-muted-foreground" />
        </div>
      );
    }

    // Don't render anything when complete - results will be in the message
    return null;
  },
});

