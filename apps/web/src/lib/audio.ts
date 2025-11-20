/**
 * Browser audio utility functions.
 */

import { getTwilioDevice } from '@/hooks/useTwilioDevice';

/**
 * Resume browser audio context.
 *
 * MUST be called from a user gesture (e.g., button click) to satisfy
 * browser security requirements for audio playback.
 *
 * This function works with Twilio Device SDK, which manages its own
 * AudioContext internally. For other audio contexts, use AudioContext.resume()
 * directly.
 *
 * @returns Promise that resolves when audio context is resumed
 */
export async function resumeAudio(): Promise<void> {
  const device = getTwilioDevice();
  if (!device?.audio) {
    return; // No-op if device not initialized (e.g., Vapi provider)
  }

  try {
    await device.audio.setInputDevice('default');
    console.log('[Audio] Audio context resumed from user gesture');
  } catch (err) {
    console.warn('[Audio] Audio resume warning:', err);
  }
}

