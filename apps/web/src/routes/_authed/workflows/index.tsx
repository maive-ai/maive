import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/_authed/workflows/')({
  component: WorkflowsPage,
});

function WorkflowsPage() {
  return (
    <section className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Workflows - Coming Soon
          </h1>
          <p className="text-lg text-gray-600">
            This feature is currently under development.
          </p>
        </div>
      </div>
    </section>
  );
}
