import { Pause, Play } from 'lucide-react';

import { Button } from '@/components/ui/button';

interface PowerDialerControlProps {
  isActive: boolean;
  onToggle: () => void;
  currentIndex: number;
  totalContacts: number;
  disabled?: boolean;
}

export function PowerDialerControl({
  isActive,
  onToggle,
  currentIndex,
  totalContacts,
  disabled = false,
}: PowerDialerControlProps) {
  return (
    <div className="flex items-center justify-between p-4 bg-gray-50 border-b">
      <div className="flex items-center gap-3">
        <Button
          onClick={onToggle}
          disabled={disabled || totalContacts === 0}
          size="sm"
          variant={isActive ? 'destructive' : 'default'}
          className="gap-2"
        >
          {isActive ? (
            <>
              <Pause className="size-4" />
              Stop Dialing
            </>
          ) : (
            <>
              <Play className="size-4" />
              Start Dialing
            </>
          )}
        </Button>
        <div className="text-sm text-gray-600">
          {totalContacts === 0 ? (
            'No contacts in call list'
          ) : isActive ? (
            <>
              Calling contact {currentIndex + 1} of {totalContacts}
            </>
          ) : (
            <>
              {totalContacts} contact{totalContacts !== 1 ? 's' : ''} ready to
              call
            </>
          )}
        </div>
      </div>
    </div>
  );
}
