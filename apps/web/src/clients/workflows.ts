// import {
//   Configuration,
//   WorkflowsApi,
//   type Workflow,
//   type WorkflowRequest,
// } from '@maive/api/client';

// import { getIdToken } from '@/auth';
// import { env } from '@/env';

// // Create a configured workflows API instance
// const createWorkflowsApi = async (): Promise<WorkflowsApi> => {
//   const token = await getIdToken();
//   if (!token) throw new Error('Not authenticated');

//   return new WorkflowsApi(
//     new Configuration({
//       accessToken: token,
//       basePath: env.PUBLIC_SERVER_URL,
//     }),
//   );
// };

// /**
//  * Fetch all workflows for the current user
//  */
// export const fetchWorkflows = async (): Promise<Workflow[]> => {
//   const api = await createWorkflowsApi();
//   const response = await api.listWorkflows();
//   return response.data;
// };

// /**
//  * Fetch a specific workflow by ID
//  */
// export const fetchWorkflow = async (workflowId: string): Promise<Workflow> => {
//   const api = await createWorkflowsApi();
//   const response = await api.getWorkflow(workflowId);
//   return response.data;
// };

// /**
//  * Create a new workflow
//  */
// export const createWorkflow = async (
//   workflowData: WorkflowRequest,
// ): Promise<Workflow> => {
//   const api = await createWorkflowsApi();
//   const response = await api.createWorkflow(workflowData);
//   return response.data;
// };

// /**
//  * Update an existing workflow
//  */
// export const updateWorkflow = async (
//   workflowId: string,
//   workflowData: WorkflowRequest,
// ): Promise<Workflow> => {
//   const api = await createWorkflowsApi();
//   const response = await api.updateWorkflow(workflowId, workflowData);
//   return response.data;
// };

// /**
//  * Delete a workflow by ID
//  */
// export const deleteWorkflow = async (workflowId: string): Promise<void> => {
//   const api = await createWorkflowsApi();
//   await api.deleteWorkflow(workflowId);
// };
