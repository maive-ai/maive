/**
 * React hook for managing Twilio Device SDK for browser-based calling.
 * Only initializes if VOICE_AI_PROVIDER=twilio on backend.
 */

import { Call, Device } from '@twilio/voice-sdk';
import { useEffect, useRef, useState } from 'react';

import { getTwilioToken, useVoiceAIProvider } from '@/clients/ai/voice';

// Global phone device reference for utility functions
let globalPhoneDevice: Device | null = null;

/**
 * Get the current Twilio Device instance (if initialized).
 * Used by utility functions that need device access without React hooks.
 */
export function getTwilioDevice(): Device | null {
  return globalPhoneDevice;
}

interface UseTwilioDeviceReturn {
  device: Device | null;
  isReady: boolean;
  activeCall: Call | null;
  error: string | null;
}

/**
 * Hook to manage Twilio Device for browser-based calling.
 *
 * Only initializes if backend is configured for Twilio provider.
 * For Vapi, returns safe defaults without initialization.
 *
 * @returns Device state and active call information
 */
export function useTwilioDevice(): UseTwilioDeviceReturn {
  const [device, setDevice] = useState<Device | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [activeCall, setActiveCall] = useState<Call | null>(null);
  const [error, setError] = useState<string | null>(null);
  const deviceRef = useRef<Device | null>(null);

  // Check if Twilio provider is configured
  const { data: provider } = useVoiceAIProvider();
  const isTwilio = provider === 'twilio';

  useEffect(() => {
    // Only initialize if Twilio is the configured provider
    if (!isTwilio || device !== null) {
      return; // Skip if not Twilio or device already initialized
    }
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
            console.log('[Twilio Device] Registered and ready');
            setIsReady(true);
          }
        });

        dev.on('error', (err) => {
          console.error('[Twilio Device] Error:', err);
          if (mounted) {
            setError(err.message);
          }
        });

        dev.on('incoming', (call: Call) => {
          console.log('[Twilio Device] Incoming call - auto-accepting');
          if (mounted) {
            setActiveCall(call);
            try {
              call.accept();
              console.log('[Twilio Device] Call accepted');
            } catch (err) {
              console.error('[Twilio Device] Failed to accept call:', err);
            }
          }
        });

        dev.on('unregistered', () => {
          if (mounted) {
            console.log('[Twilio Device] Unregistered');
            setIsReady(false);
          }
        });

        await dev.register();
        if (mounted) {
          setDevice(dev);
          deviceRef.current = dev;
          globalPhoneDevice = dev; // Update global reference
        }
      } catch (err) {
        console.error('[Twilio Device] Failed to initialize:', err);
        if (mounted) {
          setError(String(err));
        }
      }
    };

    initDevice();

    return () => {
      mounted = false;
      if (deviceRef.current) {
        deviceRef.current.unregister();
        deviceRef.current = null;
        globalPhoneDevice = null; // Clear global reference on cleanup
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isTwilio]); // Only depend on isTwilio, not device (intentional)

  return { device, isReady, activeCall, error };
}

