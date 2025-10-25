import MaiveLogo from '@maive/brand/logos/Maive-Main-Icon.png';
import { createFileRoute } from '@tanstack/react-router';
import { AlertCircle, Building2, CheckCircle2, FileText, Loader2, Mail, MapPin, Phone, User } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { Value as E164Number } from 'react-phone-number-input';
import { isValidPhoneNumber } from 'react-phone-number-input';

import { useEndCall } from '@/clients/ai/voice';
import { useFetchProject } from '@/clients/crm';
import { useCallAndWriteToCrm } from '@/clients/workflows';
import { CallAudioVisualizer } from '@/components/call/CallAudioVisualizer';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { PhoneInput } from '@/components/ui/phone-input';
import { useActiveCallPolling } from '@/hooks/useActiveCallPolling';
import { formatPhoneNumber, getStatusColor } from '@/lib/utils';

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
  const [activeCallId, setActiveCallId] = useState<string | null>(null);
  const [listenUrl, setListenUrl] = useState<string | null>(null);
  const [controlUrl, setControlUrl] = useState<string | null>(null);
  const callAndWritetoCrmMutation = useCallAndWriteToCrm(projectId);
  const endCallMutation = useEndCall();

  // Poll for active call status every 2.5 seconds
  const { data: activeCall } = useActiveCallPolling({
    onCallEnded: () => {
      console.log('[Project Detail] Call ended - clearing active call state');
      setActiveCallId(null);
      setListenUrl(null);
      setControlUrl(null);
      callAndWritetoCrmMutation.reset();
    },
  });

  // Only allow ending the call when we have the control URL
  const canEndCall = controlUrl !== null;

  const isValid = phoneNumber ? isValidPhoneNumber(phoneNumber) : false;

  // Update phone number when project data loads
  useEffect(() => {
    if (project) {
      let adjusterPhone = project.adjuster_phone || '';

      // If phone number doesn't start with +, prepend +1 (US country code)
      if (adjusterPhone && !adjusterPhone.startsWith('+')) {
        adjusterPhone = '+1' + adjusterPhone.replace(/\D/g, ''); // Remove non-digits and add +1
      }

      setPhoneNumber(adjusterPhone as E164Number | '');
    }
  }, [project]);

  // Restore active call state on mount
  useEffect(() => {
    if (activeCall && activeCall.project_id === projectId) {
      // Active call matches current project - restore state
      console.log('[Project Detail] Restoring active call state:', activeCall);
      setActiveCallId(activeCall.call_id);
      setListenUrl(activeCall.listen_url);

      // Extract control URL from provider_data
      const providerData = activeCall.provider_data as any;
      if (providerData?.monitor?.control_url) {
        setControlUrl(providerData.monitor.control_url);
      }
    } else if (activeCall && activeCall.project_id !== projectId) {
      // Active call for different project - show warning
      console.log('[Project Detail] Active call exists for different project:', activeCall.project_id);
      // TODO: Show toast/notification to user about active call on different project
    }
  }, [activeCall, projectId]);

  // Store call ID when call starts successfully
  useEffect(() => {
    if (callAndWritetoCrmMutation.isSuccess && callAndWritetoCrmMutation.data) {
      setActiveCallId(callAndWritetoCrmMutation.data.call_id);

      // Extract listenUrl and controlUrl from provider_data
      const providerData = callAndWritetoCrmMutation.data.provider_data;
      if (providerData?.monitor?.listen_url) {
        setListenUrl(providerData.monitor.listen_url);
      }
      if (providerData?.monitor?.control_url) {
        setControlUrl(providerData.monitor.control_url);
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
      customer_id: project.id,
      customer_name: providerData?.customerName,
      customer_address: providerData?.address,
      claim_number: project.claim_number || providerData?.claimNumber,
      insurance_agency: providerData?.insuranceAgency,
      adjuster_name: providerData?.adjusterName,
      adjuster_phone: providerData?.adjusterContact?.phone,
      tenant: providerData?.tenant,
      // For flat CRMs (Mock, JobNimbus), use project.id as the job_id
      // For hierarchical CRMs (Service Titan), this would need to be the actual job_id
      job_id: project.id
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
                  <CardTitle className="text-2xl">{project.customer_name || providerData?.customerName || 'Customer Name'}</CardTitle>
                </div>
                {project.status && (
                  <div className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getStatusColor(project.status)}`}>
                    {project.status}
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              
              {/* Customer Information */}
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <MapPin className="size-5 text-gray-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-medium text-gray-700">Address</p>
                    <p className="text-gray-600">{project.address_line1 || providerData?.address || 'Not available'}</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <Phone className="size-5 text-gray-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-medium text-gray-700">Phone</p>
                    <p className="text-gray-600">{formatPhoneNumber(providerData?.customer_phone || providerData?.phone)}</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <Mail className="size-5 text-gray-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-medium text-gray-700">Email</p>
                    <p className="text-gray-600 break-all">{providerData?.customer_email || providerData?.email || 'Not available'}</p>
                  </div>
                </div>
              </div>

              {/* Claim Information */}
              {(project.claim_number || project.date_of_loss || project.insurance_company) && (
                <div className="border-t pt-6 space-y-4">
                  <div className="flex items-start gap-3">
                    <FileText className="size-5 text-gray-400 mt-0.5 shrink-0" />
                    <div className="flex-1 space-y-3">
                      {project.claim_number && (
                        <div>
                          <p className="font-medium text-gray-700">Claim Number</p>
                          <p className="text-gray-600">{project.claim_number}</p>
                        </div>
                      )}
                      {project.date_of_loss && (
                        <div>
                          <p className="font-medium text-gray-700">Date of Loss</p>
                          <p className="text-gray-600">
                            {new Date(project.date_of_loss).toLocaleDateString('en-US', {
                              year: 'numeric',
                              month: 'long',
                              day: 'numeric'
                            })}
                          </p>
                        </div>
                      )}
                      {project.insurance_company && (
                        <div>
                          <p className="font-medium text-gray-700">Insurance Company</p>
                          <p className="text-gray-600">{project.insurance_company}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Notes */}
              {providerData?.notes && (
                <div className="border-t pt-6">
                  <p className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
                    Notes
                  </p>
                  <div className="space-y-3 pl-2">
                    <p className="text-gray-600 whitespace-pre-wrap">{providerData.notes}</p>
                  </div>
                </div>
              )}

              {/* Adjuster Contact */}
              {(project.adjuster_name || project.adjuster_phone || project.adjuster_email) && (
                <div className="border-t pt-6">
                  <p className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
                    Adjuster Contact
                  </p>
                  <div className="space-y-3 pl-2">
                    {project.adjuster_name && (
                      <div className="flex items-center gap-3">
                        <User className="size-4 text-gray-400" />
                        <p className="text-gray-700">{project.adjuster_name}</p>
                      </div>
                    )}
                    {project.adjuster_phone && (
                      <div className="flex items-center gap-3">
                        <Phone className="size-4 text-gray-400" />
                        <p className="text-gray-600">{formatPhoneNumber(project.adjuster_phone)}</p>
                      </div>
                    )}
                    {project.adjuster_email && (
                      <div className="flex items-center gap-3">
                        <Mail className="size-4 text-gray-400" />
                        <p className="text-gray-600 break-all">{project.adjuster_email}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
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
                  <p className="text-sm text-gray-600">Let your AI Assistant Riley check on a claim.</p>
                </div>
              </div>
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
                  disabled={callAndWritetoCrmMutation.isPending}
                />
                {phoneNumber && !isValid && (
                  <p className="text-sm text-red-600">
                    Please enter a valid phone number
                  </p>
                )}
              </div>

              {/* Success Message */}
              {callAndWritetoCrmMutation.isSuccess && callAndWritetoCrmMutation.data && (
                <div className="flex items-start gap-3 rounded-lg bg-green-50 border border-green-200 p-4">
                  <CheckCircle2 className="size-5 text-green-600 mt-0.5" />
                  <div className="flex-1 space-y-1">
                    <p className="text-sm font-medium text-green-900">
                      Call started!
                    </p>
                    <p className="text-sm text-green-700">
                      Call ID: {callAndWritetoCrmMutation.data.call_id}
                    </p>
                    <p className="text-xs text-green-600">
                      Status: {callAndWritetoCrmMutation.data.status}
                    </p>
                  </div>
                </div>
              )}

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
                    ? (endCallMutation.isPending || !canEndCall)
                    : (callAndWritetoCrmMutation.isPending || !phoneNumber || !isValid)
                }
              >
                {activeCallId ? (
                  endCallMutation.isPending ? (
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
                  )
                ) : (
                  callAndWritetoCrmMutation.isPending ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Creating Call...
                    </>
                  ) : (
                    `Start Call with ${providerData?.insuranceAgencyContact?.name || 'Contact'}`
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
