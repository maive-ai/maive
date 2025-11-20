/**
 * Phone number configuration settings component.
 */

import { Loader2, Phone, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import {
    assignPhoneNumber,
    deletePhoneNumber,
    getPhoneNumber,
    type PhoneNumberResponse,
} from '@/clients/phoneNumbers';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface PhoneNumberSettingsProps {
  onSuccess?: () => void;
}

export function PhoneNumberSettings({ onSuccess }: PhoneNumberSettingsProps) {
  const [existingConfig, setExistingConfig] = useState<PhoneNumberResponse | null>(null);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);

  // Load existing config on mount
  useEffect(() => {
    let mounted = true;

    const loadConfig = async () => {
      try {
        const config = await getPhoneNumber();
        if (mounted) {
          setExistingConfig(config);
          setPhoneNumber(config.phone_number);
        }
      } catch {
        console.log('No existing phone number config found');
      } finally {
        if (mounted) {
          setIsFetching(false);
        }
      }
    };

    loadConfig();

    return () => {
      mounted = false;
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (isLoading) return;

    setIsLoading(true);

    try {
      const config = await assignPhoneNumber({ phone_number: phoneNumber });
      setExistingConfig(config);
      toast.success('Phone number saved successfully');
      onSuccess?.();
    } catch (err) {
      console.error('Failed to assign phone number:', err);
      toast.error(err instanceof Error ? err.message : 'Failed to save phone number');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!existingConfig || isDeleting) return;

    const confirmed = window.confirm(
      'Are you sure you want to remove this phone number configuration?'
    );
    if (!confirmed) return;

    setIsDeleting(true);

    try {
      await deletePhoneNumber();
      setExistingConfig(null);
      setPhoneNumber('');
      toast.success('Phone number removed');
    } catch (err) {
      console.error('Failed to delete config:', err);
      toast.error('Failed to remove phone number');
    } finally {
      setIsDeleting(false);
    }
  };

  if (isFetching) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium">Phone Number</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Configure your phone number for outbound calls
        </p>
      </div>

      {existingConfig && (
        <div className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center gap-3">
            <Phone className="h-5 w-5 text-green-600" />
            <div>
              <p className="text-sm font-medium text-green-900">
                Phone number configured
              </p>
              <p className="text-sm text-green-700">{existingConfig.phone_number}</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDelete}
            disabled={isDeleting}
          >
            {isDeleting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4 text-red-600" />
            )}
          </Button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="phone-number">Phone Number *</Label>
            <Input
              id="phone-number"
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="+18019198371"
              required
            />
            <p className="text-xs text-muted-foreground">
              Enter in E.164 format (e.g., +1 for US, followed by area code and number)
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-4">
          <Button type="submit" disabled={isLoading} className="min-w-[180px]">
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {existingConfig ? 'Update' : 'Save'} Phone Number
          </Button>
        </div>
      </form>

      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-900">
          <strong>Note:</strong> This phone number will be used for all outbound calls
          you make via the autodialer feature.
        </p>
      </div>
    </div>
  );
}

