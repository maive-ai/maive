/**
 * Phone number client - using generated API client.
 */

import {
    Configuration,
    PhoneNumbersApi,
    type PhoneNumberCreate,
    type PhoneNumberResponse,
} from '@maive/api/client';

import { baseClient } from './base';
import { env } from '@/env';

// Re-export types from the generated client
export type { PhoneNumberCreate, PhoneNumberResponse };

/**
 * Create a configured Phone Numbers API instance using the shared axios client.
 */
const createPhoneNumbersApi = (): PhoneNumbersApi => {
  return new PhoneNumbersApi(
    new Configuration({
      basePath: env.PUBLIC_SERVER_URL,
    }),
    undefined,
    baseClient
  );
};

/**
 * Assign phone number to current user.
 */
export async function assignPhoneNumber(
  data: PhoneNumberCreate
): Promise<PhoneNumberResponse> {
  const api = createPhoneNumbersApi();
  const response = await api.assignPhoneNumberApiPhoneNumbersPost(data);
  return response.data;
}

/**
 * Get phone number for current user.
 */
export async function getPhoneNumber(): Promise<PhoneNumberResponse> {
  const api = createPhoneNumbersApi();
  const response = await api.getPhoneNumberApiPhoneNumbersGet();
  return response.data;
}

/**
 * Delete phone number assignment for current user.
 */
export async function deletePhoneNumber(): Promise<void> {
  const api = createPhoneNumbersApi();
  await api.deletePhoneNumberApiPhoneNumbersDelete();
}

