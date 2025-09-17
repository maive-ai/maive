import { createFileRoute } from '@tanstack/react-router';

import { StructuredGeneration } from '@/components/workflows/structured-generation';

export const Route = createFileRoute('/_authed/workflows/$workflowId')({
  component: WorkflowBuilderPage,
});

function WorkflowBuilderPage() {
  const { workflowId } = Route.useParams();

  return <StructuredGeneration workflowId={workflowId} />;
}
