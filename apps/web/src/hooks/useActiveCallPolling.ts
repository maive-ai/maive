import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';

import { getActiveCall, type ActiveCallState } from '@/clients/ai/voice';

interface UseActiveCallPollingOptions {
  /**
   * Whether to enable polling
   * @default true
   */
  enabled?: boolean;
  /**
   * Polling interval in milliseconds
   * @default 2500 (2.5 seconds)
   */
  pollingInterval?: number;
  /**
   * Callback when call ends (is_active changes to false)
   */
  onCallEnded?: () => void;
}

/**
 * Hook to poll for active call status and detect when call ends.
 *
 * Polls the backend every 2.5 seconds when there's an active call.
 * Automatically detects when the call ends and triggers callback.
 * Stops polling when no active call to save resources.
 *
 * @param options - Configuration options
 * @returns React Query result with active call data
 *
 * @example
 * ```tsx
 * const { data: activeCall } = useActiveCallPolling({
 *   onCallEnded: () => {
 *     console.log('Call ended!');
 *     clearCallState();
 *   }
 * });
 * ```
 */
export function useActiveCallPolling(options: UseActiveCallPollingOptions = {}) {
  const {
    enabled = true,
    pollingInterval = 2500,
    onCallEnded,
  } = options;

  const previousCallRef = useRef<ActiveCallState | null>(null);
  const callbackFiredRef = useRef(false);

  // Query active call with custom polling interval
  const query = useQuery({
    queryKey: ['active-call'],
    queryFn: getActiveCall,
    enabled,
    refetchOnMount: true,
    // Only poll if we have an active call or if we don't know yet (first query)
    refetchInterval: (query) => {
      const data = query.state.data;
      // If we have data and call is not active, don't poll
      if (data !== undefined && (!data || !data.call_id)) {
        return false;
      }
      return pollingInterval;
    },
    refetchIntervalInBackground: true,
    staleTime: 0, // Always consider stale to force refetch on interval
  });

  const { data: activeCall } = query;

  // Detect when call ends
  useEffect(() => {
    // Skip if no previous call to compare against
    if (!previousCallRef.current) {
      if (activeCall) {
        previousCallRef.current = activeCall;
        callbackFiredRef.current = false;
      }
      return;
    }

    const wasActive = previousCallRef.current.call_id != null;
    const isActive = activeCall?.call_id != null;

    // Call ended: was active, now inactive
    if (wasActive && !isActive && !callbackFiredRef.current) {
      callbackFiredRef.current = true;

      if (onCallEnded) {
        onCallEnded();
      }
    }

    // Update ref for next comparison (ALWAYS update, even when null)
    previousCallRef.current = activeCall || null;

    // Reset callback flag when new call starts
    if (!wasActive && isActive) {
      callbackFiredRef.current = false;
    }
  }, [activeCall, onCallEnded]);

  return query;
}
