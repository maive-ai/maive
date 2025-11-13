import { useMemo } from 'react';

import type { Project } from '@/clients/crm';

/**
 * Custom hook to filter projects based on a search query.
 * Searches across multiple project fields including customer name, address, phone, etc.
 *
 * @param projects - Array of projects to search through
 * @param searchQuery - Search query string
 * @returns Filtered array of projects matching the search query
 */
export function useProjectSearch(projects: Project[] | undefined, searchQuery: string): Project[] {
  return useMemo(() => {
    if (!projects || !searchQuery.trim()) {
      return projects || [];
    }

    const query = searchQuery.toLowerCase().trim();

    return projects.filter((project) => {
      const providerData = project.provider_data as any;

      // Search across multiple fields
      const searchableFields = [
        project.id,
        project.status,
        project.customer_name,
        project.claim_number,
        project.number,
        providerData?.customerName,
        providerData?.address,
        providerData?.phone,
        providerData?.email,
        providerData?.insuranceAgency,
        providerData?.insuranceAgencyContact?.name,
        providerData?.adjusterName,
        providerData?.adjusterContact?.name,
      ];

      return searchableFields.some((field) =>
        field?.toString().toLowerCase().includes(query)
      );
    });
  }, [projects, searchQuery]);
}

