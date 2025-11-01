import ShinyText from '@/components/ShinyText';
import { makeAssistantToolUI } from '@assistant-ui/react';

// Extract title from reasoning summary
// Format: "**Title**\n\nDetailed reasoning..."
// We only want "Title" for display
function extractReasoningTitle(summary: string): string {
  if (!summary || typeof summary !== 'string') {
    return 'Thinking...';
  }

  // Check if summary contains complete title (both opening and closing **)
  if (summary.includes('**')) {
    // Split by ** to extract text between first pair
    const parts = summary.split('**');
    if (parts.length >= 3 && parts[1] && parts[1].trim()) {
      return parts[1].trim(); // Text between first ** and second **
    }

    // If we only have opening ** but no closing yet, show "Thinking..."
    // This handles streaming where we might get "**" or "**Part" initially
    if (parts.length < 3) {
      return 'Thinking...';
    }
  }

  // Fallback: return first line or truncated summary
  const firstLine = summary.split('\n')[0];
  return firstLine?.trim() || 'Thinking...';
}

export const ReasoningToolUI = makeAssistantToolUI({
  toolName: 'reasoning',
  render: ({ args, result }) => {
    // Show shimmer with reasoning summary while thinking (no result yet)
    if (!result) {
      const providedTitle = typeof args?.title === 'string' ? args.title : '';
      const fullSummary = typeof args?.summary === 'string' ? args.summary : '';
      const title = extractReasoningTitle(providedTitle || fullSummary);

      return (
        <div className="mb-2">
          <ShinyText text={title} className="text-base leading-7 text-muted-foreground" />
        </div>
      );
    }

    // Don't render anything when complete - actual response will be in the message
    return null;
  },
});
