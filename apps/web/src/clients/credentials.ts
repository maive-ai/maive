// Credentials client - using generated API client

import {
  Configuration,
  CredentialsApi,
  type CRMCredentials,
  type CRMCredentialsCreate,
} from '@maive/api/client';

import { getIdToken } from '@/auth';
import { env } from '@/env';

// Re-export types from the generated client
export type { CRMCredentials, CRMCredentialsCreate };

/**
 * Create a configured Credentials API instance
 */
const createCredentialsApi = async (): Promise<CredentialsApi> => {
  const token = await getIdToken();
  if (!token) throw new Error('Not authenticated');

  return new CredentialsApi(
    new Configuration({
      accessToken: token,
      basePath: env.PUBLIC_SERVER_URL,
      baseOptions: { withCredentials: true },
    }),
  );
};

/**
 * Create CRM credentials for the user's organization
 */
export async function createCRMCredentials(
  data: CRMCredentialsCreate
): Promise<CRMCredentials> {
  const api = await createCredentialsApi();
  const response = await api.createCrmCredentialsApiCredsPost(data);
  return response.data;
}

/**
 * Get CRM credentials for the user's organization
 */
export async function getCRMCredentials(): Promise<CRMCredentials> {
  const api = await createCredentialsApi();
  const response = await api.getCrmCredentialsApiCredsGet();
  return response.data;
}

/**
 * Delete CRM credentials for the user's organization
 */
export async function deleteCRMCredentials(): Promise<void> {
  const api = await createCredentialsApi();
  await api.deleteCrmCredentialsApiCredsDelete();
}
