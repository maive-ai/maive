import ShinyText from '@/components/ShinyText';
import { makeAssistantToolUI } from '@assistant-ui/react';

export const WebSearchToolUI = makeAssistantToolUI({
  toolName: 'web_search',
  render: ({ result }) => {
    // Show shimmer while searching (no result yet)
    if (!result) {
      return (
        <div className="mb-2">
          <ShinyText text="Searching the web..." className="text-sm leading-7 text-muted-foreground" />
        </div>
      );
    }

    // Don't render anything when complete - results will be in the message
    return null;
  },
});
