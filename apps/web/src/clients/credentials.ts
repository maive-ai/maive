// Credentials client - using generated API client

import {
  Configuration,
  CredentialsApi,
  type CRMCredentials,
  type CRMCredentialsCreate,
} from '@maive/api/client';

import { env } from '@/env';
import { baseClient } from './base';

// Re-export types from the generated client
export type { CRMCredentials, CRMCredentialsCreate };

/**
 * Create a configured Credentials API instance using the shared axios client
 */
const createCredentialsApi = (): CredentialsApi => {
  return new CredentialsApi(
    new Configuration({
      basePath: env.PUBLIC_SERVER_URL,
    }),
    undefined,
    baseClient
  );
};

/**
 * Create CRM credentials for the user's organization
 */
export async function createCRMCredentials(
  data: CRMCredentialsCreate
): Promise<CRMCredentials> {
  const api = createCredentialsApi();
  const response = await api.createCrmCredentialsApiCredsPost(data);
  return response.data;
}

/**
 * Get CRM credentials for the user's organization
 */
export async function getCRMCredentials(): Promise<CRMCredentials> {
  const api = createCredentialsApi();
  const response = await api.getCrmCredentialsApiCredsGet();
  return response.data;
}

/**
 * Delete CRM credentials for the user's organization
 */
export async function deleteCRMCredentials(): Promise<void> {
  const api = createCredentialsApi();
  await api.deleteCrmCredentialsApiCredsDelete();
}
