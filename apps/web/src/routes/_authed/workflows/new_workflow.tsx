import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import type { AxiosError } from 'axios';
import { useEffect, useRef } from 'react';

import { createWorkflow } from '@/clients/workflows';
import Loading from '@/components/Loading';

export const Route = createFileRoute('/_authed/workflows/new_workflow')({
  component: NewWorkflowPage,
});

function NewWorkflowPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const workflowIdRef = useRef<string>(crypto.randomUUID());

  // Create workflow mutation
  const createWorkflowMutation = useMutation({
    mutationFn: async () => {
      return await createWorkflow({
        id: workflowIdRef.current,
        name: 'New Workflow',
        prompt: 'Extract data from the uploaded document.',
      });
    },
    onSuccess: (newWorkflow) => {
      // Invalidate workflows list to show the new workflow
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      // Navigate to the new workflow
      navigate({
        to: '/workflows/$workflowId',
        params: { workflowId: newWorkflow.id },
      });
    },
    onError: (error: AxiosError) => {
      if (error.response && error.response.status === 409) {
        console.warn(
          'Workflow with this ID already exists, likely due to React Strict Mode or rapid clicks. No new workflow created.',
        );
        // Do not navigate away, as the initial creation was successful
      } else {
        console.error('Failed to create workflow:', error);
      }
    },
  });

  // Automatically create workflow when component mounts
  useEffect(() => {
    createWorkflowMutation.mutate();
  }, []); // Empty dependency array - only run once on mount

  return <Loading />;
}
