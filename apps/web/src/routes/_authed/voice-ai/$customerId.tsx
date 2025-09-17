// Import Maive logo
import MaiveLogo from '@maive/brand/logos/Maive-Main-Icon.png';

import { useMutation } from '@tanstack/react-query';
import { Link, createFileRoute } from '@tanstack/react-router';
import { ArrowLeft, Phone } from 'lucide-react';
import { useState } from 'react';

import { useCustomer } from '@/clients/customer-crm';
import { createOutboundCall } from '@/clients/voice-ai';
import Loading from '@/components/Loading';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { CustomerDetailsComponent } from '@/components/ui/customer-details';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export const Route = createFileRoute('/_authed/voice-ai/$customerId')({
  component: CustomerVoiceAI,
});

function CustomerVoiceAI() {
  const { customerId } = Route.useParams();
  const [phoneNumber, setPhoneNumber] = useState('');

  const customerQuery = useCustomer(customerId);

  const createCallMutation = useMutation({
    mutationFn: createOutboundCall,
    onSuccess: (data) => {
      console.log('Call created:', data);
      // Reset form
      setPhoneNumber('');
    },
    onError: (error) => {
      console.error('Failed to create call:', error);
    },
  });

  const customer = customerQuery.data;

  // Set phone number when customer data loads
  if (customer && !phoneNumber) {
    setPhoneNumber(customer.phoneNumber);
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const finalPhoneNumber = phoneNumber.trim() || customer?.phoneNumber;
    if (!finalPhoneNumber) return;

    createCallMutation.mutate({
      phone_number: finalPhoneNumber,
      // Pass customer context to Riley
      customer_name: customer?.homeownerName,
      customer_address: customer?.address,
      claim_number: customer?.claimNumber,
      date_of_loss: customer?.dateOfLoss,
      insurance_agency: customer?.insuranceAgency,
      adjuster_name: customer?.adjusterName,
      adjuster_phone: customer?.adjusterContact?.phone,
      metadata: {
        source: 'web-ui',
        assistant_name: 'Riley',
        customer_id: customer?.id,
        crm_source: customer?.crmSource,
      },
    });
  };

  if (customerQuery.isLoading) {
    return <Loading />;
  }

  if (customerQuery.isError || !customer) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <p className="text-red-600">
              Error loading customer details. Please try again.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <Link
          to="/voice-ai"
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Customer Search
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Customer Details Section */}
        <div>
          <CustomerDetailsComponent customer={customer} />
        </div>

        {/* Call Initiation Section */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <img src={MaiveLogo} alt="Maive Logo" className="w-9 h-auto" />
                <div>
                  <CardTitle className="text-xl">Maive Assistant AI</CardTitle>
                  <CardDescription>
                    Let your AI Assistant Riley check on a claim
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Phone className="w-4 h-4 text-blue-600" />
                  <p className="text-sm font-medium text-blue-800">
                    
                  </p>
                </div>
              </div> */}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="phone-number">Phone Number</Label>
                  <Input
                    id="phone-number"
                    type="tel"
                    placeholder="+1234567890"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    disabled={createCallMutation.isPending}
                  />
                </div>

                <Button
                  type="submit"
                  disabled={!phoneNumber.trim() || createCallMutation.isPending}
                  className="w-full"
                >
                  <Phone className="w-4 h-4 mr-2" />
                  {createCallMutation.isPending
                    ? 'Initiating Call...'
                    : `Start Call with ${customer.insuranceAgencyContact?.name}`}
                </Button>

                {createCallMutation.isError && (
                  <Card className="border-red-200 bg-red-50">
                    <CardContent className="pt-6">
                      <p className="text-sm text-red-800">
                        <strong>Error:</strong>{' '}
                        {createCallMutation.error?.message}
                      </p>
                    </CardContent>
                  </Card>
                )}

                {createCallMutation.isSuccess && (
                  <Card className="border-green-200 bg-green-50">
                    <CardContent>
                      <p className="text-sm text-green-800">
                        <strong>Call started!</strong>
                      </p>
                    </CardContent>
                  </Card>
                )}
              </form>
            </CardContent>
          </Card>

          {/* Claim Status Stepper */}
          {/* <ClaimStatusStepper customer={customer} /> */}
        </div>
      </div>
    </div>
  );
}
