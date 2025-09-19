// Customer CRM client - using generated API client

import {
  CRMApi,
  Configuration,
  type AdjusterContact,
  type CustomerDetails,
  type InsuranceAgencyContact,
} from '@maive/api-serverless/client';
import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { getIdToken } from '@/auth';
import { env } from '@/env';

// Configuration: Set the CRM system for this contractor deployment
// TODO: Move this to environment variable in the future
const CONTRACTOR_CRM_SYSTEM: CustomerDetails['crmSource'] = 'monday';

// Re-export types from the generated client
export type { AdjusterContact, CustomerDetails, InsuranceAgencyContact };

/**
 * Create a configured CRM API instance
 */
const createCRMApi = async (): Promise<CRMApi> => {
  const token = await getIdToken();
  if (!token) throw new Error('Not authenticated');

  return new CRMApi(
    new Configuration({
      accessToken: token,
      basePath: env.PUBLIC_SERVER_URL,
    }),
  );
};

/**
 * Search customers with automatic CRM source filtering
 * This maintains compatibility with the existing frontend code
 */
export async function searchCustomers(
  query: string,
): Promise<CustomerDetails[]> {
  const api = await createCRMApi();

  // Search with CRM source filter for the configured contractor system
  const response = await api.searchCustomers(
    query.trim() || undefined,
    CONTRACTOR_CRM_SYSTEM,
    50,
  );

  return response.data.customers;
}

/**
 * Get customer by ID with CRM source validation
 * This maintains compatibility with the existing frontend code
 */
export async function getCustomerById(
  id: string,
): Promise<CustomerDetails | null> {
  const api = await createCRMApi();

  try {
    const response = await api.getCustomerById(id);
    const customer = response.data.customer;

    // Only return customers from the configured CRM system (maintains original behavior)
    return customer && customer.crmSource === CONTRACTOR_CRM_SYSTEM
      ? customer
      : null;
  } catch (error: any) {
    // Handle 404 as null (customer not found)
    if (error.response?.status === 404) {
      return null;
    }
    throw error;
  }
}

// Utility functions for CRM source handling
export function getCrmSourceLabel(
  source: CustomerDetails['crmSource'],
): string {
  switch (source) {
    case 'servicetitan':
      return 'ServiceTitan';
    case 'jobnimbus':
      return 'JobNimbus';
    case 'acculynx':
      return 'AccuLynx';
    case 'monday':
      return 'Monday.com';
    default:
      return source;
  }
}

export function getCrmSourceColor(
  source: CustomerDetails['crmSource'],
): string {
  switch (source) {
    case 'servicetitan':
      return 'bg-blue-100 text-blue-800';
    case 'jobnimbus':
      return 'bg-green-100 text-green-800';
    case 'acculynx':
      return 'bg-purple-100 text-purple-800';
    case 'monday':
      return 'bg-orange-100 text-orange-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

export function getCrmSourceLogo(
  source: CustomerDetails['crmSource'],
): string | null {
  switch (source) {
    case 'servicetitan':
      return '@maive/brand/logos/integrations/servicetitan/ServiceTitan_Logo_Black_2.png';
    case 'jobnimbus':
      return '@maive/brand/logos/integrations/jobnimbus/jobnimbus_logo.png';
    case 'acculynx':
      return '@maive/brand/logos/integrations/acculynx/acculynx_logo.png';
    case 'monday':
      return '@maive/brand/logos/integrations/monday/monday_logo.png';
    default:
      return null;
  }
}

export function getConfiguredCrmLabel(): string {
  return getCrmSourceLabel(CONTRACTOR_CRM_SYSTEM);
}

export function getConfiguredCrmLogo(): string | null {
  return getCrmSourceLogo(CONTRACTOR_CRM_SYSTEM);
}

export function getConfiguredCrmSystem(): CustomerDetails['crmSource'] {
  return CONTRACTOR_CRM_SYSTEM;
}

// React Query hooks for customer data with polling

/**
 * Hook to get customer data with automatic 3-second polling
 */
export function useCustomer(
  customerId: string,
): UseQueryResult<CustomerDetails | null, Error> {
  return useQuery({
    queryKey: ['customer', customerId],
    queryFn: () => getCustomerById(customerId),
    staleTime: 3 * 1000, // Data is fresh for 3 seconds
    refetchInterval: 3 * 1000, // Poll every 3 seconds
    refetchIntervalInBackground: true, // Continue polling when tab is not focused
    enabled: !!customerId, // Only run query if customerId exists
  });
}

/**
 * Hook to search customers with automatic polling
 */
export function useCustomers(
  searchQuery: string,
): UseQueryResult<CustomerDetails[], Error> {
  return useQuery({
    queryKey: ['customers', searchQuery],
    queryFn: () => searchCustomers(searchQuery),
    staleTime: 30 * 1000, // Data is fresh for 30 seconds
    refetchInterval: 30 * 1000, // Poll every 30 seconds
    refetchIntervalInBackground: true, // Continue polling when tab is not focused
  });
}
