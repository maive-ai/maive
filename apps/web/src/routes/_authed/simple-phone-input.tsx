import { useCallAndWriteResultsToCrm } from '@/clients/workflows';
import { Button } from '@/components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { PhoneInput } from '@/components/ui/phone-input';
import { createFileRoute } from '@tanstack/react-router';
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { useState } from 'react';
import type { E164Number } from 'react-phone-number-input';
import { isValidPhoneNumber } from 'react-phone-number-input';

export const Route = createFileRoute('/_authed/simple-phone-input')({
  component: SimplePhoneInput,
});

function SimplePhoneInput() {
  const [phoneNumber, setPhoneNumber] = useState<E164Number | ''>('');
  const createCallMutation = useCallAndWriteResultsToCrm();

  const isValid = phoneNumber ? isValidPhoneNumber(phoneNumber) : false;

  const handleStartCall = (): void => {
    if (!phoneNumber || !isValid) {
      return;
    }

    createCallMutation.mutate({
      phone_number: phoneNumber,
    });
  };

  return (
    <div className="flex h-full justify-center bg-white p-6">
      <div className="w-full max-w-2xl space-y-6">
        {/* Page Header */}
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-3">
            Voice AI Call
          </h1>
          <p className="text-lg text-gray-600">
            Enter a phone number to start an AI-powered call
          </p>
        </div>

        {/* Call Details Card */}
        <Card className="w-full">
          <CardHeader>
            <CardTitle>Call Details</CardTitle>
            <CardDescription>Enter phone number to initiate call</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="phone-number">Phone Number</Label>
              <PhoneInput
                id="phone-number"
                placeholder="Enter phone number"
                value={phoneNumber}
                onChange={(value) => setPhoneNumber(value || '')}
                defaultCountry="US"
                disabled={createCallMutation.isPending}
              />
              {phoneNumber && !isValid && (
                <p className="text-sm text-red-600">
                  Please enter a valid phone number
                </p>
              )}
            </div>

            {/* Success Message */}
            {createCallMutation.isSuccess && createCallMutation.data && (
              <div className="flex items-start gap-3 rounded-lg bg-green-50 border border-green-200 p-4">
                <CheckCircle2 className="size-5 text-green-600 mt-0.5" />
                <div className="flex-1 space-y-1">
                  <p className="text-sm font-medium text-green-900">
                    Call initiated successfully!
                  </p>
                  <p className="text-sm text-green-700">
                    Call ID: {createCallMutation.data.call_id}
                  </p>
                  <p className="text-xs text-green-600">
                    Status: {createCallMutation.data.status}
                  </p>
                </div>
              </div>
            )}

            {/* Error Message */}
            {createCallMutation.isError && (
              <div className="flex items-start gap-3 rounded-lg bg-red-50 border border-red-200 p-4">
                <AlertCircle className="size-5 text-red-600 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-red-900">
                    Failed to create call
                  </p>
                  <p className="text-sm text-red-700">
                    {createCallMutation.error?.message || 'An unexpected error occurred'}
                  </p>
                </div>
              </div>
            )}

            <Button
              onClick={handleStartCall}
              className="w-full"
              size="lg"
              disabled={createCallMutation.isPending || !phoneNumber || !isValid}
            >
              {createCallMutation.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Creating Call...
                </>
              ) : (
                'Start Voice AI Call'
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
