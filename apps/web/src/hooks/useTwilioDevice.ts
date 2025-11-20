/**
 * React hook for managing Twilio Device SDK for browser-based calling.
 */

import { Call, Device } from '@twilio/voice-sdk';
import { useEffect, useState } from 'react';

import { getTwilioToken } from '@/clients/ai/voice';

interface UseTwilioDeviceReturn {
  device: Device | null;
  isReady: boolean;
  activeCall: Call | null;
  error: string | null;
}

/**
 * Hook to manage Twilio Device for browser-based calling.
 *
 * Initializes the Twilio Device with an access token from the backend
 * and manages the connection lifecycle.
 *
 * @returns Device state and active call information
 */
export function useTwilioDevice(): UseTwilioDeviceReturn {
  const [device, setDevice] = useState<Device | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [activeCall, setActiveCall] = useState<Call | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const initDevice = async () => {
      try {
        const twilioToken = await getTwilioToken();

        const dev = new Device(twilioToken, {
          codecPreferences: [Call.Codec.Opus, Call.Codec.PCMU],
          enableImprovedSignalingErrorPrecision: true,
        });

        dev.on('registered', () => {
          if (mounted) {
            console.log('[Twilio] Device registered and ready');
            setIsReady(true);
          }
        });

        dev.on('error', (err) => {
          console.error('[Twilio] Device error:', err);
          if (mounted) {
            setError(err.message);
          }
        });

        dev.on('incoming', (call: Call) => {
          console.log('[Twilio] Incoming call');
          if (mounted) {
            setActiveCall(call);
            // Auto-accept for autodialer
            call.accept();
          }
        });

        dev.on('unregistered', () => {
          if (mounted) {
            console.log('[Twilio] Device unregistered');
            setIsReady(false);
          }
        });

        await dev.register();
        if (mounted) {
          setDevice(dev);
        }
      } catch (err) {
        console.error('[Twilio] Failed to initialize device:', err);
        if (mounted) {
          setError(String(err));
        }
      }
    };

    initDevice();

    return () => {
      mounted = false;
      device?.unregister();
    };
  }, [device]);

  return { device, isReady, activeCall, error };
}

