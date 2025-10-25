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
    queryFn: async () => {
      console.log('[Active Call Polling] Making API request to /calls/active');
      const result = await getActiveCall();
      console.log('[Active Call Polling] API response:', result);
      return result;
    },
    enabled,
    refetchOnMount: true,
    // Only poll if we have an active call or if we don't know yet (first query)
    refetchInterval: (query) => {
      const data = query.state.data;
      console.log('[Active Call Polling] Determining refetch interval. Data:', data, 'Will poll:', data === undefined || (data && data.call_id));
      // If we have data and call is not active, don't poll
      if (data !== undefined && (!data || !data.call_id)) {
        console.log('[Active Call Polling] Stopping polling - no active call');
        return false;
      }
      console.log(`[Active Call Polling] Continuing to poll every ${pollingInterval}ms`);
      return pollingInterval;
    },
    refetchIntervalInBackground: true,
    staleTime: 0, // Always consider stale to force refetch on interval
  });

  const { data: activeCall } = query;

  // Detect when call ends
  useEffect(() => {
    console.log('[Active Call Polling] Effect triggered:', {
      previousCall: previousCallRef.current?.call_id || 'none',
      currentCall: activeCall?.call_id || 'none',
      callbackFired: callbackFiredRef.current,
    });

    // Skip if no previous call to compare against
    if (!previousCallRef.current) {
      if (activeCall) {
        console.log('[Active Call Polling] Initializing with call:', activeCall.call_id);
        previousCallRef.current = activeCall;
        callbackFiredRef.current = false;
      }
      return;
    }

    const wasActive = previousCallRef.current.call_id != null;
    const isActive = activeCall?.call_id != null;

    console.log('[Active Call Polling] State check:', { wasActive, isActive });

    // Call ended: was active, now inactive
    if (wasActive && !isActive && !callbackFiredRef.current) {
      console.log('[Active Call Polling] Call ended - triggering callback');
      callbackFiredRef.current = true;

      if (onCallEnded) {
        onCallEnded();
      }
    }

    // Update ref for next comparison (ALWAYS update, even when null)
    previousCallRef.current = activeCall || null;

    // Reset callback flag when new call starts
    if (!wasActive && isActive) {
      console.log('[Active Call Polling] New call started, resetting callback flag');
      callbackFiredRef.current = false;
    }
  }, [activeCall, onCallEnded]);

  return query;
}
