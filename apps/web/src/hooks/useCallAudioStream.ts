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

  const setupPlayer = (): void => {
    // Initialize PCMPlayer with built-in analyser
    const player = new PCMPlayer({
      inputCodec: 'Int16',
      channels: 1,
      sampleRate: 32000,
      flushTime: 100,
      fftSize: FFT_SIZE,
    });
    playerRef.current = player;
    
    // Use PCMPlayer's built-in analyser
    analyserRef.current = player.analyserNode;
    
    startVolumeMonitoring();
    
    // Try to resume if suspended (autoplay policy)
    if (player.audioCtx.state === 'suspended') {
      player.audioCtx.resume().catch((err: Error) => {
        console.warn('[Audio Stream] AudioContext suspended (user interaction required):', err);
      });
    }
  };
  
  const handleWebSocketMessage = (event: MessageEvent): void => {
    if (event.data instanceof ArrayBuffer) {
      playerRef.current?.feed(event.data);
    }
  };
  
  const handleWebSocketOpen = (): void => {
    console.log('[Audio Stream] WebSocket connected');
    isConnectingRef.current = false;
    setState(prev => ({ ...prev, isConnected: true, error: null }));
  };
  
  const handleWebSocketError = (event: Event): void => {
    console.error('[Audio Stream] WebSocket error:', event);
    isConnectingRef.current = false;
    setState(prev => ({ ...prev, error: 'Connection error' }));
  };
  
  const handleWebSocketClose = (): void => {
    isConnectingRef.current = false;
    stopVolumeMonitoring();
    setState(prev => ({ ...prev, isConnected: false, volumeLevel: 0 }));
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
    if (!listenUrl || wsRef.current || isConnectingRef.current) return;
    
    console.log('[Audio Stream] Attempting to connect to:', listenUrl);
    isConnectingRef.current = true;
    
    try {
      setupPlayer();
      setupWebSocket(listenUrl);
    } catch (err) {
      console.error('[Audio Stream] Failed to connect:', err);
      isConnectingRef.current = false;
      setState(prev => ({ ...prev, error: 'Failed to connect' }));
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
      
      setState(prev => ({ ...prev, volumeLevel: normalizedVolume }));
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

