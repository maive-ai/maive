import MaiveLogo from '@maive/brand/logos/Maive-Main-Icon.png';

import { createFileRoute } from '@tanstack/react-router';
import { AlertCircle, Building2, FileText, Loader2, Mail, MapPin, Phone, User } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { Value as E164Number } from 'react-phone-number-input';
import { isValidPhoneNumber, parsePhoneNumber } from 'react-phone-number-input';

import { useEndCall } from '@/clients/ai/voice';
import { useFetchProject } from '@/clients/crm';
import { useCallAndWriteToCrm } from '@/clients/workflows';
import { E164PhoneInput } from '@/components/E164PhoneInput';
import { CallAudioVisualizer } from '@/components/call/CallAudioVisualizer';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { getStatusColor } from '@/lib/utils';

export const Route = createFileRoute('/_authed/project-detail')({
  component: ProjectDetail,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      projectId: search.projectId as string,
    };
  },
});

function ProjectDetail() {
  const { projectId } = Route.useSearch();
  const { data: project, isLoading, isError } = useFetchProject(projectId);
  
  // Initialize hooks before any early returns
  const providerData = project?.provider_data as any;
  const [phoneNumber, setPhoneNumber] = useState<E164Number | ''>('');
  // Country parsing handled by E164PhoneInput
  const [activeCallId, setActiveCallId] = useState<string | null>(null);
  const [listenUrl, setListenUrl] = useState<string | null>(null);
  const callAndWritetoCrmMutation = useCallAndWriteToCrm();
  const endCallMutation = useEndCall();

  const isValid = phoneNumber ? isValidPhoneNumber(phoneNumber) : false;

  // Update phone number when project data loads
  useEffect(() => {
    if (project && providerData) {
      const insurancePhone = providerData?.insuranceAgencyContact?.phone || providerData?.phone || '';
      
      if (insurancePhone) {
        try {
          // Parse the phone number to get E.164 format
          const parsedPhone = parsePhoneNumber(insurancePhone);
          if (parsedPhone) {
            // Set the full E.164 number - the component will auto-detect country and format
            setPhoneNumber(parsedPhone.number as E164Number);
            // Country handled by E164PhoneInput
          } else {
            // If parsing fails, just set the phone number as-is
            setPhoneNumber(insurancePhone as E164Number);
          }
        } catch (error) {
          // If parsing fails, just set the phone number as-is
          console.warn('Failed to parse phone number:', insurancePhone, error);
          setPhoneNumber(insurancePhone as E164Number);
        }
      } else {
        setPhoneNumber('');
      }
    }
  }, [project, providerData]);

  // Store call ID when call starts successfully
  useEffect(() => {
    if (callAndWritetoCrmMutation.isSuccess && callAndWritetoCrmMutation.data) {
      setActiveCallId(callAndWritetoCrmMutation.data.call_id);
      
      // Extract listenUrl from provider_data
      const providerData = callAndWritetoCrmMutation.data.provider_data;
      console.log('[Project Detail] Provider data:', providerData);
      if (providerData?.monitor?.listenUrl) {
        console.log('[Project Detail] Setting listenUrl:', providerData.monitor.listenUrl);
        setListenUrl(providerData.monitor.listenUrl);
      } else {
        console.log('[Project Detail] No listenUrl found in provider_data');
      }
    }
  }, [callAndWritetoCrmMutation.isSuccess, callAndWritetoCrmMutation.data]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <Loader2 className="size-8 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading project details...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (isError || !project) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <AlertCircle className="size-8 text-red-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Project not found
          </h2>
          <p className="text-gray-600">
            The project you&apos;re looking for doesn&apos;t exist or has been removed.
          </p>
        </div>
      </div>
    );
  }

  const handleStartCall = (): void => {
    if (!phoneNumber || !isValid) {
      return;
    }

    callAndWritetoCrmMutation.mutate({
      phone_number: phoneNumber,
      // Pass customer details from project data
      customer_id: project.project_id,
      customer_name: providerData?.customerName,
      customer_address: providerData?.address,
      claim_number: providerData?.claimNumber,
      insurance_agency: providerData?.insuranceAgency,
      adjuster_name: providerData?.adjusterName,
      adjuster_phone: providerData?.adjusterContact?.phone,
      tenant: providerData?.tenant,
      job_id: providerData?.job_id,
    });
  };

  const handleEndCall = (): void => {
    if (!activeCallId) return;
    
    endCallMutation.mutate(activeCallId, {
      onSuccess: () => {
        setActiveCallId(null);
        setListenUrl(null);
        callAndWritetoCrmMutation.reset();
      }
    });
  };

  return (
    <div className="flex h-full bg-white p-6">
      <div className="w-full max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Left Column: Project Details */}
        <div className="space-y-6">
          <Card className="w-full">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-lg bg-gradient-to-br from-orange-400 to-pink-400 flex items-center justify-center">
                  <Building2 className="size-6 text-white" />
                </div>
                <div className="flex-1">
                  <CardTitle className="text-2xl">{providerData?.customerName || 'Customer Name'}</CardTitle>
                </div>
                <div className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getStatusColor(project.status)}`}>
                  {project.status}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              
              {/* Customer Information */}
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <MapPin className="size-5 text-gray-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-medium text-gray-700">Address</p>
                    <p className="text-gray-600">{providerData?.address || 'Address not available'}</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <Phone className="size-5 text-gray-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-medium text-gray-700">Phone</p>
                    <p className="text-gray-600">{providerData?.phone || 'Phone not available'}</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <Mail className="size-5 text-gray-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-medium text-gray-700">Email</p>
                    <p className="text-gray-600 break-all">{providerData?.email || 'Email not available'}</p>
                  </div>
                </div>
              </div>

              {/* Notes and Claim Number & Insurance */}
              <div className="border-t pt-6 space-y-4">
                {/* Claim Number & Insurance */}
                <div className="flex items-start gap-3">
                  <FileText className="size-5 text-gray-400 mt-0.5 shrink-0" />
                  <div className="flex-1 grid grid-cols-2 gap-4">
                    <div>
                      <p className="font-medium text-gray-700">Claim Number</p>
                      <p className="text-gray-600">{providerData?.claimNumber || 'Not available'}</p>
                    </div>
                    <div>
                      <p className="font-medium text-gray-700">Insurance Agency</p>
                      <p className="text-gray-600">{providerData?.insuranceAgency || 'Not available'}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Adjuster Contact */}
              <div className="border-t pt-6">
                <p className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
                  Adjuster Contact
                </p>
                <div className="space-y-3 pl-2">
                  <div className="flex items-center gap-3">
                    <User className="size-4 text-gray-400" />
                    <p className="text-gray-700">{providerData?.adjusterContact?.name || 'Not available'}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Phone className="size-4 text-gray-400" />
                    <p className="text-gray-600">{providerData?.adjusterContact?.phone || 'Not available'}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Mail className="size-4 text-gray-400" />
                    <p className="text-gray-600 break-all">{providerData?.adjusterContact?.email || 'Not available'}</p>
                  </div>
                </div>
              </div>

              {/* Notes */}
              <div className="border-t pt-6">
                <p className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
                  Notes
                </p>
                <div className="space-y-3 pl-2">
                  <p className="text-gray-600 whitespace-pre-wrap">{providerData?.notes || 'No notes'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Voice AI Interface */}
        <div className="space-y-6">
          <Card className="w-full">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="size-8 flex items-center justify-center">
                  <img 
                    src={MaiveLogo} 
                    alt="Maive Logo" 
                    className="w-12 h-auto"
                  />
                </div>
                <div>
                  <CardTitle className="text-xl">Maive Assistant AI</CardTitle>
                  <p className="text-sm text-gray-600">Initiate a call with your AI Assistant to check on a claim.</p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="phone-number">Phone Number</Label>
                <E164PhoneInput
                  id="phone-number"
                  placeholder="Enter phone number"
                  value={phoneNumber}
                  onChange={(value) => setPhoneNumber(value || '')}
                  disabled={callAndWritetoCrmMutation.isPending}
                />
                {phoneNumber && !isValid && (
                  <p className="text-sm text-red-600">
                    Please enter a valid phone number
                  </p>
                )}
              </div>

              {/* Error Message */}
              {callAndWritetoCrmMutation.isError && (
                <div className="flex items-start gap-3 rounded-lg bg-red-50 border border-red-200 p-4">
                  <AlertCircle className="size-5 text-red-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-red-900">
                      Failed to create call
                    </p>
                    <p className="text-sm text-red-700">
                      {callAndWritetoCrmMutation.error?.message || 'An unexpected error occurred'}
                    </p>
                  </div>
                </div>
              )}

              <Button
                onClick={activeCallId ? handleEndCall : handleStartCall}
                className="w-full"
                size="lg"
                variant={activeCallId ? "destructive" : "default"}
                disabled={
                  activeCallId 
                    ? endCallMutation.isPending 
                    : (callAndWritetoCrmMutation.isPending || !phoneNumber || !isValid)
                }
              >
                {activeCallId ? (
                  endCallMutation.isPending ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Ending Call...
                    </>
                  ) : (
                    'End Call'
                  )
                ) : (
                  callAndWritetoCrmMutation.isPending ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Creating Call...
                    </>
                  ) : (
                    `Start Call with ${providerData?.adjusterContact?.name || 'Contact'}`
                  )
                )}
              </Button>

              <CallAudioVisualizer 
                listenUrl={listenUrl} 
                onDisconnect={() => setListenUrl(null)}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
