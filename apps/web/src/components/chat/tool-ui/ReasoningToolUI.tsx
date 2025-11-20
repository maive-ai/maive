import { makeAssistantToolUI } from '@assistant-ui/react';
import ShinyText from '@/components/ShinyText';

export const ReasoningToolUI = makeAssistantToolUI({
  toolName: 'reasoning',
  render: ({ args, result }) => {
    // Show shimmer with reasoning summary while thinking (no result yet)
    if (!result) {
      // Use the actual reasoning summary from the model, fallback to default message
      const rawSummary =
        (args as { summary?: string })?.summary || 'Planning next steps...';

      // Strip markdown formatting since ShinyText doesn't support it
      // Remove incomplete markdown patterns (leading/trailing ** without pairs)
      const summary = rawSummary
        .replace(/^\**\s*/g, '') // Remove leading asterisks and whitespace
        .replace(/\s*\**$/g, '') // Remove trailing asterisks and whitespace
        .trim();

      return (
        <div className="mb-2">
          <ShinyText
            text={summary}
            className="text-base leading-7 text-muted-foreground"
          />
        </div>
      );
    }
  },
});
