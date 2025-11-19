import { makeAssistantToolUI } from '@assistant-ui/react';
import ShinyText from '@/components/ShinyText';

export const FileSearchToolUI = makeAssistantToolUI({
  toolName: 'file_search',
  render: ({ result }) => {
    // Show shimmer while searching (no result yet)
    if (!result) {
      return (
        <div className="mb-2">
          <ShinyText
            text="Finding the latest data..."
            className="text-base leading-7 text-muted-foreground"
          />
        </div>
      );
    }

    // Don't render anything when complete - results will be in the message
    return null;
  },
});
