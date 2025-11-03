import ShinyText from '@/components/ShinyText';
import { makeAssistantToolUI } from '@assistant-ui/react';


export const ReasoningToolUI = makeAssistantToolUI({
  toolName: 'reasoning',
  render: ({ result }) => {
    // Show shimmer with reasoning summary while thinking (no result yet)
    if (!result) {

      return (
        <div className="mb-2">
          <ShinyText text={"Planning next steps..."} className="text-sm leading-6 text-muted-foreground" />
        </div>
      );
    }
  },
});
