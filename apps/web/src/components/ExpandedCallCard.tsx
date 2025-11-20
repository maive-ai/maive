import {
  CheckCircle2,
  Clock,
  FileText,
  Loader2,
  MapPin,
  Phone,
  PhoneCall,
  User,
} from 'lucide-react';

import { CallAudioVisualizer } from '@/components/call/CallAudioVisualizer';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Item,
  ItemActions,
  ItemContent,
  ItemFooter,
  ItemHeader,
  ItemMedia,
  ItemTitle,
} from '@/components/ui/item';
import { Spinner } from '@/components/ui/spinner';
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
  onDisconnect: () => void;
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
  onDisconnect,
  isEndingCall,
}: ExpandedCallCardProps) {
  return (
    <Item variant="outline" className="flex-col items-start">
      {/* Header with status badge */}
      <ItemHeader>
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
      </div>

      {/* Call status message */}
      {callStatus && (
        <div
          className={`w-full rounded-lg p-3 mt-3 flex items-start gap-3 ${
            callStatus === 'in_progress'
              ? 'bg-green-50 border border-green-200'
              : callStatus === 'ringing' || callStatus === 'queued'
                ? 'bg-blue-50 border border-blue-200'
                : 'bg-gray-50 border border-gray-200'
          }`}
        >
          <div className="flex-1">
            <p
              className={`text-sm font-medium ${
                callStatus === 'in_progress'
                  ? 'text-green-900'
                  : callStatus === 'ringing' || callStatus === 'queued'
                    ? 'text-blue-900'
                    : 'text-gray-900'
              }`}
            >
              {callStatus === 'queued' && 'Call queued'}
              {callStatus === 'ringing' && 'Call ringing...'}
              {callStatus === 'in_progress' && 'Call in progress'}
              {!['queued', 'ringing', 'in_progress'].includes(callStatus) &&
                'Call started'}
            </p>
            <p
              className={`text-xs mt-0.5 ${
                callStatus === 'in_progress'
                  ? 'text-green-700'
                  : callStatus === 'ringing' || callStatus === 'queued'
                    ? 'text-blue-700'
                    : 'text-gray-700'
              }`}
            >
              {callStatus === 'queued' && 'Waiting in queue...'}
              {callStatus === 'ringing' && 'Waiting for answer...'}
              {callStatus === 'in_progress' &&
                'Connected - You can now listen to the call'}
              {!['queued', 'ringing', 'in_progress'].includes(callStatus) &&
                `Status: ${callStatus}`}
            </p>
          </div>
        </div>
      )}

      {/* Call controls footer */}
      <ItemFooter className="pt-3">
        <ItemActions className="w-full">
          <Button
            onClick={onEndCall}
            variant="destructive"
            size="sm"
            disabled={isEndingCall || !canEndCall}
            className="flex-1"
          >
            {isEndingCall ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Ending Call...
              </>
            ) : !canEndCall ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Connecting...
              </>
            ) : (
              'End Call'
            )}
          </Button>
        </ItemActions>
      </ItemFooter>

      {/* Live Listen Audio Visualizer */}
      <div className="w-full">
        <CallAudioVisualizer
          listenUrl={listenUrl}
          callStatus={callStatus}
          onDisconnect={onDisconnect}
        />
      </div>
    </Item>
  );
}
