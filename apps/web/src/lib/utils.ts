import { useMutation } from '@tanstack/react-query';
import { clsx, type ClassValue } from 'clsx';
import { useEffect, useRef } from 'react';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Custom hook for auto-saving data with debouncing
 * Follows React Query patterns for optimistic updates and error handling
 */
export function useAutoSave<T extends Record<string, any>>(
  data: T,
  saveFunction: (data: T) => Promise<any>,
  options: {
    debounceMs?: number;
    enabled?: boolean;
    onSuccess?: (result: any) => void;
    onError?: (error: Error) => void;
  } = {},
) {
  const { debounceMs = 1000, enabled = true, onSuccess, onError } = options;

  const timeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const previousDataRef = useRef<T>(data);

  const mutation = useMutation({
    mutationFn: saveFunction,
    onSuccess: (result) => {
      console.log('✅ Auto-save successful:', result);
      onSuccess?.(result);
    },
    onError: (error) => {
      console.error('❌ Auto-save failed:', error);
      onError?.(error);
    },
  });

  useEffect(() => {
    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Skip if disabled or no changes
    if (
      !enabled ||
      JSON.stringify(data) === JSON.stringify(previousDataRef.current)
    ) {
      return;
    }

    // Set new timeout for debounced save
    timeoutRef.current = setTimeout(() => {
      // Double-check that data hasn't changed since timeout was set
      if (JSON.stringify(data) !== JSON.stringify(previousDataRef.current)) {
        mutation.mutate(data);
        previousDataRef.current = data;
      }
    }, debounceMs);

    // Cleanup timeout on unmount or dependency change
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [data, debounceMs, enabled]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    isSaving: mutation.isPending,
    saveError: mutation.isError,
    lastSaved: mutation.isSuccess ? new Date() : null,
    retry: mutation.reset,
  };
}

/**
 * Get color classes for project status badges
 */
export function getStatusColor(status: string): string {
  switch (status) {
    case 'Scheduled':
      return 'bg-blue-100 text-blue-800';
    case 'Dispatched':
      return 'bg-purple-100 text-purple-800';
    case 'In Progress':
      return 'bg-yellow-100 text-yellow-800';
    case 'Hold':
      return 'bg-red-100 text-red-800';
    case 'Completed':
      return 'bg-green-100 text-green-800';
    case 'Canceled':
      return 'bg-gray-100 text-gray-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

/**
 * Format a phone number for display
 * Supports US phone numbers in various formats
 *
 * Examples:
 * - "8881234568" -> "(888) 123-4568"
 * - "+18881234568" -> "(888) 123-4568"
 * - "888-123-4568" -> "(888) 123-4568"
 */
export function formatPhoneNumber(phone: string | null | undefined): string {
  if (!phone) return 'Not available';

  // Remove all non-digit characters
  const digits = phone.replace(/\D/g, '');

  // Handle US phone numbers (10 or 11 digits)
  if (digits.length === 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  } else if (digits.length === 11 && digits[0] === '1') {
    return `(${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }

  // If not a standard format, return as-is
  return phone;
}

/**
 * Extract adjuster information from a project with fallbacks for different data structures.
 * Handles both direct fields and nested provider_data structures.
 *
 * @param project - The project object containing adjuster data
 * @returns Object with adjuster name and phone, or default values if not found
 */
export function getAdjusterInfo(project: {
  adjuster_name?: string | null;
  adjuster_phone?: string | null;
  provider_data?: any;
}): { name: string; phone: string } {
  const providerData = project.provider_data;

  const name =
    project.adjuster_name ||
    providerData?.adjusterName ||
    providerData?.adjusterContact?.name ||
    'No adjuster';

  const phone =
    project.adjuster_phone ||
    providerData?.adjusterPhone ||
    providerData?.adjusterContact?.phone ||
    'No phone';

  return { name, phone };
}

