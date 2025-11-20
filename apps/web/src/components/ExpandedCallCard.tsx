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
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import {
  Item,
  ItemContent,
  ItemHeader,
  ItemMedia,
  ItemTitle,
} from '@/components/ui/item';
import { Toggle } from '@/components/ui/toggle';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
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
  callStatus: string | null;
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

  const canListen = callStatus === 'in_progress' && listenUrl;

  return (
    <Item variant="outline" className="flex-col items-start">
      {/* Header with status badge and call controls */}
      <ItemHeader>
        <div className="flex items-center gap-2">
          <Badge className={`${getStatusColor(projectStatus)} pointer-events-none`}>
            {projectStatus}
          </Badge>
          {callStatus && (
            <div className="flex items-center gap-2">
              {callStatus === 'in_progress' ? (
                <PhoneCall className="size-4 text-green-600 animate-pulse" />
              ) : callStatus === 'ringing' ? (
                <Loader2 className="size-4 text-blue-600 animate-spin" />
              ) : callStatus === 'queued' ? (
                <Clock className="size-4 text-blue-600" />
              ) : (
                <CheckCircle2 className="size-4 text-gray-600" />
              )}
              <span className="text-xs font-medium text-gray-600 capitalize">
                {callStatus === 'in_progress' ? 'Connected' : callStatus}
              </span>
            </div>
          )}
        </div>

        {/* Call control buttons */}
        <TooltipProvider>
          <div className="flex items-center gap-1">
            {/* Live Listen Toggle */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Toggle
                  pressed={!!(isListening && canListen)}
                  onPressedChange={setIsListening}
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
                  : isListening
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

      {/* Main content with contact info */}
      <div className="flex items-start gap-4 w-full">
        <ItemMedia variant="icon">
          <Phone className="size-4" />
        </ItemMedia>
        <ItemContent>
          <ItemTitle>{adjusterName}</ItemTitle>
          <div className="text-sm text-gray-600">
            {formatPhoneNumber(adjusterPhone)}
          </div>
        </ItemContent>
      </div>

      {/* Customer details */}
      <div className="w-full space-y-3 pt-2 border-t mt-2">
        <div className="flex items-start gap-3">
          <User className="size-4 text-gray-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">
              Homeowner
            </p>
            <p className="text-sm text-gray-900">{customerName}</p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <MapPin className="size-4 text-gray-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">
              Address
            </p>
            <p className="text-sm text-gray-900">{address}</p>
          </div>
        </div>

        {claimNumber && (
          <div className="flex items-start gap-3">
            <FileText className="size-4 text-gray-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">
                Claim Number
              </p>
              <p className="text-sm text-gray-900">{claimNumber}</p>
            </div>
          </div>
        )}

        {/* Placeholder for claim summary - to be implemented later */}
        <div className="bg-gray-50 rounded p-3 text-xs text-gray-600 leading-relaxed">
          <p className="font-medium text-gray-700 mb-1">Claim Summary</p>
          <p>
            Following up on claim status and payment timeline. Verify estimate
            approval and schedule next steps.
          </p>
        </div>

        {/* Audio visualization when listening */}
        {isListening && canListen && (
          <div className="mt-3 pt-3 border-t">
            <div className="flex items-center gap-2 text-xs text-gray-600 mb-2">
              <Headphones className="size-3" />
              <span>Listening to call...</span>
            </div>
          </div>
        )}
      </div>
    </Item>
  );
}
