import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/_authed/voice-ai/')({
  component: VoiceAI,
});

function VoiceAI() {
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Voice AI - Coming Soon
        </h1>
        <p className="text-lg text-gray-600">
          This feature is currently under development.
        </p>
      </div>
    </div>
  );
}
