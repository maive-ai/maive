import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, createFileRoute, useNavigate } from '@tanstack/react-router';
import { AlertTriangle, FileText, SquarePlus } from 'lucide-react';
import { useState } from 'react';

import { deleteWorkflow, fetchWorkflows } from '@/clients/workflows';

import { Button } from '@/components/ui/button';

export const Route = createFileRoute('/_authed/workflows/')({
  component: WorkflowsPage,
});

function WorkflowsPage() {
  const navigate = useNavigate();

  const {
    data: workflows = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['workflows'],
    queryFn: fetchWorkflows,
  });

  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteWorkflow(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflows'] }),
  });

  const handleCreateNewWorkflow = () => {
    navigate({ to: '/workflows/new_workflow' });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const toggleDropdown = (workflowId: string) => {
    setActiveDropdown(activeDropdown === workflowId ? null : workflowId);
  };

  if (isLoading) {
    return (
      <section className="p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-gray-900">My Workflows</h1>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {/* Loading skeleton */}
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-white rounded-lg border shadow-sm p-4 animate-pulse"
              >
                <div className="h-6 bg-gray-200 rounded mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="p-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center py-12">
            <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-6" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Failed to load workflows
            </h3>
            <p className="text-gray-500 mb-4">
              There was an error loading your workflows. Please try again.
            </p>
            <Button onClick={() => window.location.reload()}>Retry</Button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900">My Workflows</h1>
          <Button onClick={handleCreateNewWorkflow}>
            <SquarePlus className="h-5 w-5" /> New Workflow
          </Button>
        </div>

        {workflows.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-16 h-16 text-gray-400 mx-auto mb-6" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No workflows yet
            </h3>
            <p className="text-gray-500 mb-4">
              Create your first workflow to get started with AI-powered document
              processing
            </p>
            <Button onClick={handleCreateNewWorkflow}>
              <SquarePlus className="h-5 w-5" /> Create Your First Workflow
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {workflows.map((workflow) => (
              <div
                key={workflow.id}
                className="bg-white rounded-lg border shadow-sm hover:shadow-md transition-shadow relative"
              >
                <Link
                  to="/workflows/$workflowId"
                  params={{ workflowId: workflow.id }}
                  className="block p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-gray-900 text-lg leading-tight pr-8">
                      {workflow.name}
                    </h3>
                  </div>
                  <p className="text-sm text-gray-500 mb-3">
                    Created {formatDate(workflow.created_at)}
                  </p>
                  <p className="text-sm text-gray-600 line-clamp-2">
                    {workflow.prompt}
                  </p>
                </Link>

                {/* Three-dot menu */}
                <div className="absolute top-4 right-4">
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      toggleDropdown(workflow.id);
                    }}
                    className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <svg
                      className="w-5 h-5"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                    </svg>
                  </button>

                  {activeDropdown === workflow.id && (
                    <div className="absolute right-0 mt-1 w-48 bg-white border rounded-md shadow-lg z-10">
                      <div className="py-1">
                        <Button
                          variant="ghost"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setActiveDropdown(null);
                            if (
                              window.confirm(
                                `Delete "${workflow.name}"? This cannot be undone.`,
                              )
                            ) {
                              deleteMutation.mutate(workflow.id);
                            }
                          }}
                          className="block w-full text-left text-red-600 hover:bg-red-50"
                        >
                          Delete
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
