import { CallStatus } from '@maive/api/client';
import {
  CheckCircle2,
  Clock,
  FileText,
  Headphones,
  Loader2,
  MapPin,
  Phone,
  PhoneCall,
  PhoneOff,
  User,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import {
  Item,
  ItemHeader
} from '@/components/ui/item';
import { Toggle } from '@/components/ui/toggle';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useCallAudioStream } from '@/hooks/useCallAudioStream';
import { formatPhoneNumber, getStatusColor } from '@/lib/utils';

interface ExpandedCallCardProps {
  // Contact being called
  adjusterName: string;
  adjusterPhone: string;

  // Project/Customer details
  customerName: string;
  address: string;
  claimNumber?: string;
  projectStatus: string;

  // Call state
  callStatus: CallStatus | null;
  listenUrl: string | null;
  canEndCall: boolean;

  // Actions
  onEndCall: () => void;
  isEndingCall: boolean;
}

export function ExpandedCallCard({
  adjusterName,
  adjusterPhone,
  customerName,
  address,
  claimNumber,
  projectStatus,
  callStatus,
  listenUrl,
  canEndCall,
  onEndCall,
  isEndingCall,
}: ExpandedCallCardProps) {
  const [isListening, setIsListening] = useState(true); // Default to listening
  const { volumeLevel, isConnected, connect, disconnect } =
    useCallAudioStream(listenUrl);

  const canListen = callStatus === CallStatus.InProgress && listenUrl;

  // Auto-connect when call becomes in progress (default to listening)
  useEffect(() => {
    if (canListen && isListening && !isConnected) {
      connect();
    }
  }, [canListen, isListening, isConnected, connect]);

  // Disconnect when toggled off
  useEffect(() => {
    if (!isListening && isConnected) {
      disconnect();
    }
  }, [isListening, isConnected, disconnect]);

  // Auto-disconnect when listenUrl is removed
  useEffect(() => {
    if (!listenUrl && isConnected) {
      disconnect();
    }
  }, [listenUrl, isConnected, disconnect]);

  const handleListenToggle = (pressed: boolean) => {
    setIsListening(pressed);
    if (pressed && canListen) {
      connect();
    } else if (isConnected) {
      disconnect();
    }
  };

  return (
    <Item variant="outline" className="flex-col items-start">
      {/* SECTION 1: Call Status Information */}
      <div className="w-full">
        <ItemHeader>
          {callStatus && (
            <div className="flex items-center gap-2">
              {callStatus === CallStatus.InProgress ? (
                <PhoneCall className="size-4 text-green-600 animate-pulse" />
              ) : callStatus === CallStatus.Ringing ? (
                <Loader2 className="size-4 text-blue-600 animate-spin" />
              ) : callStatus === CallStatus.Queued ? (
                <Clock className="size-4 text-blue-600" />
              ) : (
                <CheckCircle2 className="size-4 text-gray-600" />
              )}
              <span className="text-xs font-medium text-gray-600 capitalize">
                {callStatus === CallStatus.InProgress ? 'Connected' : callStatus}
              </span>
            </div>
          )}

          {/* Call control buttons */}
          <TooltipProvider>
            <div className="flex items-center gap-1">
              {/* Live Listen Toggle */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Toggle
                    pressed={isConnected}
                    onPressedChange={handleListenToggle}
                    disabled={!canListen}
                    size="sm"
                    aria-label="Toggle live listen"
                  >
                    <Headphones className="size-4" />
                  </Toggle>
                </TooltipTrigger>
                <TooltipContent>
                  {!canListen
                    ? 'Live listen available when connected'
                    : isConnected
                      ? 'Stop listening'
                      : 'Listen to call'}
                </TooltipContent>
              </Tooltip>

              {/* End Call Button */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Toggle
                    pressed={false}
                    onPressedChange={onEndCall}
                    disabled={isEndingCall || !canEndCall}
                    size="sm"
                    aria-label="End call"
                    className="data-[state=on]:bg-destructive data-[state=on]:text-destructive-foreground hover:bg-destructive/90 hover:text-destructive-foreground"
                  >
                    {isEndingCall ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <PhoneOff className="size-4" />
                    )}
                  </Toggle>
                </TooltipTrigger>
                <TooltipContent>
                  {isEndingCall
                    ? 'Ending call...'
                    : !canEndCall
                      ? 'Connecting...'
                      : 'End call'}
                </TooltipContent>
              </Tooltip>
            </div>
          </TooltipProvider>
        </ItemHeader>

        {/* Audio visualization when listening */}
        {isConnected && (
          <div className="px-4 pb-3">
            <div className="flex items-center gap-2 text-xs text-green-600">
              <Headphones className="size-3 animate-pulse" />
              <span>Listening to call...</span>
              {volumeLevel > 0 && (
                <span className="text-gray-500">
                  Volume: {Math.round(volumeLevel * 100)}%
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* SECTION 2: Contact Info Side by Side */}
      <div className="w-full grid grid-cols-2 gap-4 pt-3 border-t">
        {/* Contact/Adjuster Info */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase">
            Contact
          </p>
          <div className="flex items-start gap-2">
            <Phone className="size-4 text-gray-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-gray-900">
                {adjusterName}
              </p>
              <p className="text-xs text-gray-600">
                {formatPhoneNumber(adjusterPhone)}
              </p>
            </div>
          </div>
        </div>

        {/* Homeowner Info */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase">
            Homeowner
          </p>
          <div className="flex items-start gap-2">
            <User className="size-4 text-gray-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-gray-900">
                {customerName}
              </p>
              <div className="flex items-start gap-1 mt-1">
                <MapPin className="size-3 text-gray-400 mt-0.5 shrink-0" />
                <p className="text-xs text-gray-600">{address}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Claim Number if available */}
      {claimNumber && (
        <div className="w-full px-4 pt-2">
          <div className="flex items-center gap-2">
            <FileText className="size-3 text-gray-400" />
            <span className="text-xs text-gray-500">Claim:</span>
            <span className="text-xs font-medium text-gray-900">
              {claimNumber}
            </span>
          </div>
        </div>
      )}

      {/* SECTION 3: Claim Summary */}
      <div className="w-full pt-3 border-t">
        <div className="bg-gray-50 rounded p-3">
          <div className="flex items-center gap-2 mb-1.5">
            <p className="text-xs font-semibold text-gray-700">
              Claim Summary
            </p>
            <Badge className={`${getStatusColor(projectStatus)} pointer-events-none`}>
              {projectStatus}
            </Badge>
          </div>
          <p className="text-xs text-gray-600 leading-relaxed">
            Following up on claim status and payment timeline. Verify estimate
            approval and schedule next steps.
          </p>
        </div>
      </div>
    </Item>
  );
}
