import { useEffect, useRef, useState } from 'react';

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
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingQueueRef = useRef(false);
  const nextPlayTimeRef = useRef(0);
  
  // Minimum buffer: Wait for 4 chunks (~53ms at 48kHz) before starting playback
  const MIN_BUFFER_CHUNKS = 4;
  
  const connect = () => {
    if (!listenUrl || wsRef.current) return;
    
    try {
      const ws = new WebSocket(listenUrl);
      wsRef.current = ws;
      
      // Let AudioContext use native sample rate (browser will handle resampling)
      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;
      
      // Create analyser for volume tracking
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;
      
      // Start volume monitoring
      startVolumeMonitoring();
      
      ws.onopen = () => {
        console.log('[Audio Stream] WebSocket connected');
        setState(prev => ({ ...prev, isConnected: true, error: null }));
      };
      
      ws.onmessage = (event) => {
        if (event.data instanceof Blob) {
          // Queue the chunk for buffered playback
          event.data.arrayBuffer().then(arrayBuffer => {
            audioQueueRef.current.push(arrayBuffer);
            
            // Start processing queue only after minimum buffer is reached
            if (!isPlayingQueueRef.current && audioQueueRef.current.length >= MIN_BUFFER_CHUNKS) {
              processAudioQueue();
            }
          });
        }
      };
      
      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setState(prev => ({ ...prev, error: 'Connection error' }));
      };
      
      ws.onclose = () => {
        stopVolumeMonitoring();
        setState(prev => ({ ...prev, isConnected: false, isPlaying: false, volumeLevel: 0 }));
      };
    } catch (err) {
      console.error('Failed to connect:', err);
      setState(prev => ({ ...prev, error: 'Failed to connect' }));
    }
  };
  
  const processAudioQueue = () => {
    const audioContext = audioContextRef.current;
    const analyser = analyserRef.current;
    
    if (!audioContext || !analyser || audioQueueRef.current.length === 0) {
      isPlayingQueueRef.current = false;
      return;
    }
    
    isPlayingQueueRef.current = true;
    
    // Initialize play time to current time if not set
    if (nextPlayTimeRef.current < audioContext.currentTime) {
      nextPlayTimeRef.current = audioContext.currentTime;
    }
    
    // Process all queued chunks
    while (audioQueueRef.current.length > 0) {
      const arrayBuffer = audioQueueRef.current.shift();
      if (arrayBuffer) {
        scheduleAudioChunk(arrayBuffer);
      }
    }
    
    isPlayingQueueRef.current = false;
  };
  
  const scheduleAudioChunk = (arrayBuffer: ArrayBuffer) => {
    const audioContext = audioContextRef.current;
    const analyser = analyserRef.current;
    
    if (!audioContext || !analyser) return;
    
    try {
      // Vapi sends 48kHz, 16-bit PCM (CD-quality audio)
      const SAMPLE_RATE = 48000;
      const pcmData = new Int16Array(arrayBuffer);
      
      // Create audio buffer
      const audioBuffer = audioContext.createBuffer(1, pcmData.length, SAMPLE_RATE);
      const channelData = audioBuffer.getChannelData(0);
      
      // Convert Int16 to Float32
      for (let i = 0; i < pcmData.length; i++) {
        const sample = pcmData[i];
        if (sample !== undefined) {
          channelData[i] = sample / 32768.0;
        }
      }
      
      // Schedule playback
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(analyser);
      analyser.connect(audioContext.destination);
      source.start(nextPlayTimeRef.current);
      
      // Update next play time
      nextPlayTimeRef.current += audioBuffer.duration;
      
      // Check if buffer is running low (less than 2 chunks)
      const bufferAheadTime = nextPlayTimeRef.current - audioContext.currentTime;
      if (audioQueueRef.current.length < 2 && bufferAheadTime < 0.08) {
        console.warn('[Audio Stream] Buffer running low, may experience gaps');
      }
      
      setState(prev => ({ ...prev, isPlaying: true }));
    } catch (error) {
      console.error('[Audio Stream] Schedule error:', error);
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
      const normalizedVolume = average / 255;
      
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
  
  const disconnect = () => {
    stopVolumeMonitoring();
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    
    analyserRef.current = null;
    audioQueueRef.current = [];
    isPlayingQueueRef.current = false;
    nextPlayTimeRef.current = 0;
    setState({ isConnected: false, isPlaying: false, volumeLevel: 0, error: null });
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

