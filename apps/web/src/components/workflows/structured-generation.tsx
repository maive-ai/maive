interface StructuredGenerationProps {
  workflowId: string;
}

export function StructuredGeneration({
  workflowId,
}: StructuredGenerationProps) {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-primary-900 mb-4">
          Building in Progress
        </h1>
        <p className="text-primary-600">
          This feature is currently under development.
        </p>
      </div>
    </div>
  );
}
