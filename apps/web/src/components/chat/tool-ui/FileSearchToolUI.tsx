import { makeAssistantToolUI } from '@assistant-ui/react';
import { ShimmerText } from '@/components/ui/shimmer-text';

export const FileSearchToolUI = makeAssistantToolUI({
  toolName: 'file_search',
  render: ({ result }) => {
    // Show shimmer while searching (no result yet)
    if (!result) {
      return (
        <div className="mb-2">
          <ShimmerText className="text-sm text-muted-foreground">
            Finding the latest data...
          </ShimmerText>
        </div>
      );
    }

    // Don't render anything when complete - results will be in the message
    return null;
  },
});
