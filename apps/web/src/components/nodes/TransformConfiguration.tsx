import { makeAssistantVisible } from '@assistant-ui/react';
import { BarChart3 } from 'lucide-react';
import React from 'react';

interface TransformConfigurationProps {
  prompt: string;
  onPromptChange: (value: string) => void;
}

// Define a simple Textarea component
const PromptTextarea: React.FC<React.ComponentPropsWithoutRef<'textarea'>> = (
  props,
) => <textarea {...props} />;

// Create an assistant-visible textarea component
const AssistantVisibleTextarea = makeAssistantVisible(PromptTextarea, {
  editable: true,
});

export function TransformConfiguration({
  prompt,
  onPromptChange,
}: TransformConfigurationProps) {
  return (
    <div className="bg-primary-50 rounded-xl shadow-sm border-2 border-primary-600 p-8">
      <div className="flex items-center gap-3 mb-8">
        <BarChart3 className="w-6 h-6 text-primary-700" />
        <h2 className="text-xl font-bold text-primary-900">Prompt</h2>
      </div>

      <div>
        <AssistantVisibleTextarea
          id="ai-prompt"
          value={prompt}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
            onPromptChange(e.target.value)
          }
          placeholder="Enter the default prompt for this workflow. This will be used for AI analysis..."
          className="w-full p-4 border-2 border-primary-400 rounded-lg focus:border-primary-600 focus:outline-none resize-none text-primary-900 placeholder-primary-500 bg-primary-50"
          rows={8}
        />
      </div>
    </div>
  );
}
