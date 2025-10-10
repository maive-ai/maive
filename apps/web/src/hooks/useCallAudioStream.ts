import { useEffect, useRef, useState } from 'react';

const SAMPLE_RATE = 48000;
const FFT_SIZE = 256;
const UINT8_MAX_VALUE = 255;
interface AudioStreamState {
  isConnected: boolean;
  isPlaying: boolean;
  volumeLevel: number; // Add volume tracking (0-1)
  error: string | null;
}

export function useCallAudioStream(listenUrl: string | null) {
  const [state, setState] = useState<AudioStreamState>({
    isConnected: false,
    isPlaying: false,
    volumeLevel: 0,
    error: null,
  });
  
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const volumeIntervalRef = useRef<number | null>(null);
  const nextPlayTimeRef = useRef(0);
  const isConnectingRef = useRef(false);
  
  const createAudioBuffer = (arrayBuffer: ArrayBuffer): AudioBuffer | null => {
    const audioContext = audioContextRef.current;
    if (!audioContext) return null;
    
    const pcmData = new Int16Array(arrayBuffer);
    const audioBuffer = audioContext.createBuffer(1, pcmData.length, SAMPLE_RATE);
    const channelData = audioBuffer.getChannelData(0);
    
    // Convert Int16 PCM to Float32
    for (let i = 0; i < pcmData.length; i++) {
      const sample = pcmData[i];
      if (sample !== undefined) {
        channelData[i] = sample / 32768.0;
      }
    }
    
    return audioBuffer;
  };
  
  const playAudioChunk = (arrayBuffer: ArrayBuffer): void => {
    const audioContext = audioContextRef.current;
    const analyser = analyserRef.current;
    
    if (!audioContext || !analyser) return;
    
    try {
      const audioBuffer = createAudioBuffer(arrayBuffer);
      if (!audioBuffer) return;
      
      // Initialize play time on first chunk
      if (nextPlayTimeRef.current < audioContext.currentTime) {
        nextPlayTimeRef.current = audioContext.currentTime;
      }
      
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(analyser);
      analyser.connect(audioContext.destination);
      source.start(nextPlayTimeRef.current);
      
      nextPlayTimeRef.current += audioBuffer.duration;
      setState(prev => ({ ...prev, isPlaying: true }));
    } catch (error) {
      console.error('[Audio Stream] Playback error:', error);
    }
  };
  
  const setupAudioContext = (): void => {
    const audioContext = new AudioContext();
    audioContextRef.current = audioContext;
    
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = FFT_SIZE;
    analyserRef.current = analyser;
    
    startVolumeMonitoring();
  };
  
  const handleWebSocketMessage = (event: MessageEvent): void => {
    if (event.data instanceof Blob) {
      event.data.arrayBuffer().then(playAudioChunk);
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
    setState(prev => ({ ...prev, isConnected: false, isPlaying: false, volumeLevel: 0 }));
  };
  
  const setupWebSocket = (url: string): void => {
    const ws = new WebSocket(url);
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
      setupAudioContext();
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
  
  const cleanupAudioContext = (): void => {
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    analyserRef.current = null;
  };
  
  const resetState = (): void => {
    nextPlayTimeRef.current = 0;
    isConnectingRef.current = false;
    setState({ isConnected: false, isPlaying: false, volumeLevel: 0, error: null });
  };
  
  const disconnect = () => {
    stopVolumeMonitoring();
    cleanupWebSocket();
    cleanupAudioContext();
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

