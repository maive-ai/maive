import PCMPlayer from 'pcm-player';
import { useEffect, useRef, useState } from 'react';

const FFT_SIZE = 256;
const UINT8_MAX_VALUE = 255;

interface AudioStreamState {
  isConnected: boolean;
  volumeLevel: number;
  error: string | null;
}

export function useCallAudioStream(listenUrl: string | null) {
  const [state, setState] = useState<AudioStreamState>({
    isConnected: false,
    volumeLevel: 0,
    error: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const playerRef = useRef<PCMPlayer | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const volumeIntervalRef = useRef<number | null>(null);
  const isConnectingRef = useRef(false);
  const lastMessageTimeRef = useRef<number>(0);
  const messageCountRef = useRef<number>(0);
  const healthCheckIntervalRef = useRef<number | null>(null);

  // Note: THESE SETTINGS NEED TO BE TUNED BASED ON THE AGENT
  // The following settings work for an agent that was STT -> TTS -> Audio Stream, but they sound bad after switching to a speech-to-speech agent.
  /*
  - Input Codec: Int16
  - Channels: 2
  - Sample Rate: 16000
  - Flush Time: 150
  - FFT Size: 256
  */
  // Good settings for a speech-to-speech agent
  /*
 - Input Codec: Int16
 - Channels: 1
 - Sample Rate: 48000
 - Flush Time: 150
 - FFT Size: 256
 */
  const setupPlayer = (): void => {
    // Initialize PCMPlayer with built-in analyser
    const player = new PCMPlayer({
      inputCodec: 'Int16',
      channels: 2,
      sampleRate: 16000, // Match Vapi's stream format
      flushTime: 50, // Reduced buffer to prevent audio loss when WebSocket closes
      fftSize: FFT_SIZE,
    });
    playerRef.current = player;

    // Use PCMPlayer's built-in analyser
    analyserRef.current = player.analyserNode;

    startVolumeMonitoring();

    // Try to resume if suspended (autoplay policy)
    if (player.audioCtx.state === 'suspended') {
      player.audioCtx.resume().catch((err: Error) => {
        console.warn(
          '[Audio Stream] AudioContext suspended (user interaction required):',
          err,
        );
      });
    }
  };

  const handleWebSocketMessage = (event: MessageEvent): void => {
    if (event.data instanceof ArrayBuffer) {
      lastMessageTimeRef.current = Date.now();
      messageCountRef.current += 1;

      // Log every 100th message to track data flow without spamming
      if (messageCountRef.current % 100 === 0) {
        console.log(
          '[Audio Stream] Received messages:',
          messageCountRef.current,
          'Latest size:',
          event.data.byteLength,
          'bytes',
        );
      }

      playerRef.current?.feed(event.data);
    } else {
      console.warn(
        '[Audio Stream] Received non-ArrayBuffer message:',
        typeof event.data,
      );
    }
  };

  const startHealthCheck = (): void => {
    // Check every 5 seconds if we're still receiving audio data
    healthCheckIntervalRef.current = window.setInterval(() => {
      const timeSinceLastMessage = Date.now() - lastMessageTimeRef.current;
      const ws = wsRef.current;

      if (ws && ws.readyState === WebSocket.OPEN) {
        if (timeSinceLastMessage > 10000) {
          // 10 seconds without data
          console.warn(
            '[Audio Stream] No audio data received for',
            Math.round(timeSinceLastMessage / 1000),
            'seconds. WebSocket state:',
            ws.readyState,
          );
        }
      }
    }, 5000);
  };

  const stopHealthCheck = (): void => {
    if (healthCheckIntervalRef.current) {
      clearInterval(healthCheckIntervalRef.current);
      healthCheckIntervalRef.current = null;
    }
  };

  const handleWebSocketOpen = (): void => {
    console.log('[Audio Stream] WebSocket connected');
    isConnectingRef.current = false;
    lastMessageTimeRef.current = Date.now();
    messageCountRef.current = 0;
    startHealthCheck();
    setState((prev) => ({ ...prev, isConnected: true, error: null }));
  };

  const handleWebSocketError = (event: Event): void => {
    console.error('[Audio Stream] WebSocket error:', event);
    isConnectingRef.current = false;
    setState((prev) => ({ ...prev, error: 'Connection error' }));
  };

  const handleWebSocketClose = (event: CloseEvent): void => {
    console.log(
      '[Audio Stream] WebSocket closed',
      'Code:',
      event.code,
      'Reason:',
      event.reason || 'none',
      'Clean:',
      event.wasClean,
      'Total messages received:',
      messageCountRef.current,
    );
    isConnectingRef.current = false;
    stopHealthCheck();
    stopVolumeMonitoring();
    cleanupPlayer();
    wsRef.current = null; // Clear the ref so we can reconnect
    setState((prev) => ({ ...prev, isConnected: false, volumeLevel: 0 }));
  };

  const setupWebSocket = (url: string): void => {
    const ws = new WebSocket(url);
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;

    ws.onopen = handleWebSocketOpen;
    ws.onmessage = handleWebSocketMessage;
    ws.onerror = handleWebSocketError;
    ws.onclose = handleWebSocketClose;
  };

  const connect = () => {
    if (!listenUrl) {
      console.warn('[Audio Stream] Cannot connect: No listenUrl provided');
      return;
    }

    // If there's an existing WebSocket, check its state
    if (wsRef.current) {
      const readyState = wsRef.current.readyState;
      // WebSocket.CLOSED (3) or WebSocket.CLOSING (2) - clean it up and reconnect
      if (readyState === WebSocket.CLOSED || readyState === WebSocket.CLOSING) {
        console.log(
          '[Audio Stream] Cleaning up stale WebSocket before reconnecting',
        );
        disconnect();
      } else {
        // WebSocket.CONNECTING (0) or WebSocket.OPEN (1) - don't interrupt
        console.warn(
          '[Audio Stream] Cannot connect: WebSocket already active',
          {
            readyState,
          },
        );
        return;
      }
    }

    if (isConnectingRef.current) {
      console.warn('[Audio Stream] Cannot connect: Already connecting');
      return;
    }

    console.log('[Audio Stream] Attempting to connect to:', listenUrl);
    isConnectingRef.current = true;

    try {
      setupPlayer();
      setupWebSocket(listenUrl);
    } catch (err) {
      console.error('[Audio Stream] Failed to connect:', err);
      isConnectingRef.current = false;
      setState((prev) => ({ ...prev, error: 'Failed to connect' }));
    }
  };

  const startVolumeMonitoring = () => {
    const analyser = analyserRef.current;
    if (!analyser) return;

    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    const updateVolume = () => {
      analyser.getByteFrequencyData(dataArray);

      // Calculate average volume (0-255 range)
      const sum = dataArray.reduce((acc, val) => acc + val, 0);
      const average = sum / dataArray.length;

      // Normalize to 0-1 range
      const normalizedVolume = average / UINT8_MAX_VALUE;

      setState((prev) => ({ ...prev, volumeLevel: normalizedVolume }));
    };

    volumeIntervalRef.current = window.setInterval(updateVolume, 50); // Update every 50ms
  };

  const stopVolumeMonitoring = () => {
    if (volumeIntervalRef.current) {
      clearInterval(volumeIntervalRef.current);
      volumeIntervalRef.current = null;
    }
  };

  const cleanupWebSocket = (): void => {
    if (!wsRef.current) return;

    const ws = wsRef.current;
    ws.onopen = null;
    ws.onmessage = null;
    ws.onerror = null;
    ws.onclose = null;
    ws.close();
    wsRef.current = null;
  };

  const cleanupPlayer = (): void => {
    if (playerRef.current) {
      playerRef.current.destroy();
      playerRef.current = null;
    }
    analyserRef.current = null;
  };

  const resetState = (): void => {
    isConnectingRef.current = false;
    setState({ isConnected: false, volumeLevel: 0, error: null });
  };

  const disconnect = () => {
    console.log(
      '[Audio Stream] Disconnecting... Total messages received:',
      messageCountRef.current,
    );
    stopHealthCheck();
    stopVolumeMonitoring();
    cleanupWebSocket();
    cleanupPlayer();
    resetState();
  };

  useEffect(() => {
    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    ...state,
    connect,
    disconnect,
  };
}
