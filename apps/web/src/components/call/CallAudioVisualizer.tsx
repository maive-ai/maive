import { motion, AnimatePresence } from 'framer-motion';
import { Phone, PhoneOff, Loader2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { useCallAudioStream } from '@/hooks/useCallAudioStream';

interface CallAudioVisualizerProps {
  listenUrl: string | null;
  callStatus?: string | null;
  onDisconnect?: () => void;
}

export function CallAudioVisualizer({
  listenUrl,
  callStatus,
  onDisconnect,
}: CallAudioVisualizerProps) {
  const { volumeLevel, isConnected, error, connect, disconnect } =
    useCallAudioStream(listenUrl);
  const [bars, setBars] = useState(Array(50).fill(5));

  // Only allow connection when call is actually in progress
  const canConnect = callStatus === 'in_progress';

  const updateBars = useCallback((volume: number) => {
    setBars(
      Array(50)
        .fill(0)
        .map(() => Math.random() * volume * 150),
    );
  }, []);

  const resetBars = useCallback(() => {
    setBars(Array(50).fill(5));
  }, []);

  // Update bars based on volume level
  useEffect(() => {
    if (isConnected) {
      updateBars(volumeLevel);
    } else {
      resetBars();
    }
  }, [volumeLevel, isConnected, updateBars, resetBars]);

  // Auto-disconnect when listenUrl is removed
  useEffect(() => {
    if (!listenUrl && isConnected) {
      disconnect();
    }
  }, [listenUrl, isConnected, disconnect]);

  const handleToggle = () => {
    if (isConnected) {
      disconnect();
      onDisconnect?.();
    } else if (canConnect) {
      connect();
    }
  };

  const micPulseAnimation = {
    scale: [1, 1.2, 1],
    opacity: [1, 0.8, 1],
    transition: { duration: 0.8, repeat: Infinity },
  };

  if (!listenUrl) return null;

  return (
    <div className="border-t pt-4">
      <div className="flex flex-col items-center justify-center p-6 rounded">
        <AnimatePresence>
          {isConnected && (
            <motion.div
              className="flex items-center justify-center w-full h-32"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.5 }}
            >
              <svg
                width="100%"
                height="100%"
                viewBox="0 0 1000 200"
                preserveAspectRatio="xMidYMid meet"
              >
                {bars.map((height, index) => (
                  <g key={index}>
                    <rect
                      x={500 + index * 20 - 490}
                      y={100 - height / 2}
                      width="10"
                      height={height}
                      className="fill-current text-primary-900 opacity-70"
                    />
                    <rect
                      x={500 - index * 20 - 10}
                      y={100 - height / 2}
                      width="10"
                      height={height}
                      className="fill-current text-primary-900 opacity-70"
                    />
                  </g>
                ))}
              </svg>
            </motion.div>
          )}
        </AnimatePresence>

        <motion.div
          className="mt-4 flex flex-col items-center gap-2"
          animate={isConnected && volumeLevel === 0 ? micPulseAnimation : {}}
        >
          <Button
            onClick={handleToggle}
            variant={isConnected ? 'destructive' : 'outline'}
            size="lg"
            className="flex items-center gap-2"
            disabled={!isConnected && !canConnect}
          >
            <AnimatePresence mode="wait">
              {isConnected ? (
                <motion.div
                  key="phone-off"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  transition={{ duration: 0.3 }}
                  className="flex items-center gap-2"
                >
                  <PhoneOff className="size-4" />
                  Stop Listening
                </motion.div>
              ) : canConnect ? (
                <motion.div
                  key="phone"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  transition={{ duration: 0.3 }}
                  className="flex items-center gap-2"
                >
                  <Phone className="size-4" />
                  Listen to Call
                </motion.div>
              ) : (
                <motion.div
                  key="waiting"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  transition={{ duration: 0.3 }}
                  className="flex items-center gap-2"
                >
                  <Loader2 className="size-4 animate-spin" />
                  Waiting for Answer
                </motion.div>
              )}
            </AnimatePresence>
          </Button>

          {error && <p className="text-sm text-red-600">{error}</p>}
        </motion.div>
      </div>
    </div>
  );
}
