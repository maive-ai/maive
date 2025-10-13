import { ClaimStatus, Status } from '@maive/api/client';
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
    case Status.Scheduled:
      return 'bg-blue-100 text-blue-800';
    case Status.Dispatched:
      return 'bg-purple-100 text-purple-800';
    case Status.InProgress:
      return 'bg-yellow-100 text-yellow-800';
    case Status.Hold:
      return 'bg-red-100 text-red-800';
    case Status.Completed:
      return 'bg-green-100 text-green-800';
    case Status.Canceled:
      return 'bg-gray-100 text-gray-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}

/**
 * Get color classes for claim status badges
 */
export function getClaimStatusColor(claimStatus: string): string {
  let colorClass: string;

  switch (claimStatus) {
    case ClaimStatus.None:
      colorClass = 'bg-gray-100 text-gray-800';
      break;
    case ClaimStatus.PendingReview:
      colorClass = 'bg-yellow-100 text-yellow-800';
      break;
    case ClaimStatus.WorkNeeded:
      colorClass = 'bg-blue-100 text-blue-800';
      break;
    case ClaimStatus.PartiallyApproved:
      colorClass = 'bg-orange-100 text-orange-800';
      break;
    case ClaimStatus.FullyApproved:
      colorClass = 'bg-green-100 text-green-800';
      break;
    case ClaimStatus.Denied:
      colorClass = 'bg-red-100 text-red-800';
      break;
    default:
      colorClass = 'bg-gray-100 text-gray-800';
      console.warn(`[Utils] Unknown claim status: ${claimStatus}, using default gray color`);
  }
  return colorClass;
}
