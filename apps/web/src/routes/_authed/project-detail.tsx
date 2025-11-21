import { CallStatus, VoiceAIProvider } from '@maive/api/client';
import MaiveLogo from '@maive/brand/logos/Maive-Main-Icon.png';
import { createFileRoute } from '@tanstack/react-router';
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  Clock,
  Download,
  FileText,
  Loader2,
  Mail,
  MapPin,
  Phone,
  PhoneCall,
  User,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  isValidPhoneNumber,
  type Value as E164Number,
} from 'react-phone-number-input';

import { useEndCall, useVoiceAIProvider } from '@/clients/ai/voice';
import { downloadFile, useFetchJobFiles, useFetchProject } from '@/clients/crm';
import { useCallAndWriteToCrm } from '@/clients/workflows';
import { CallAudioVisualizer } from '@/components/call/CallAudioVisualizer';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { PhoneInput } from '@/components/ui/phone-input';
import { useActiveCallPolling } from '@/hooks/useActiveCallPolling';
import { resumeAudio } from '@/lib/audio';
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
  const { data: files, isLoading: filesLoading } = useFetchJobFiles(projectId);

  // Initialize hooks before any early returns
  const providerData = project?.provider_data as any;
  const [phoneNumber, setPhoneNumber] = useState<E164Number | ''>('');
  const [activeCallId, setActiveCallId] = useState<string | null>(null);
  const [callStatus, setCallStatus] = useState<CallStatus | null>(null);
  const [listenUrl, setListenUrl] = useState<string | null>(null);
  const [controlUrl, setControlUrl] = useState<string | null>(null);
  const [downloadingFileId, setDownloadingFileId] = useState<string | null>(
    null,
  );
  const callAndWritetoCrmMutation = useCallAndWriteToCrm(projectId);
  const endCallMutation = useEndCall();

  // Check voice AI provider (Twilio vs Vapi)
  const { data: voiceProvider } = useVoiceAIProvider();

  // Poll for active call status every 2.5 seconds
  const { data: activeCall } = useActiveCallPolling({
    onCallEnded: () => {
      console.log('[Project Detail] Call ended - clearing active call state');
      setActiveCallId(null);
      setCallStatus(null);
      setListenUrl(null);
      setControlUrl(null);
      callAndWritetoCrmMutation.reset();
    },
  });

  // Determine if we can end the call
  // For Vapi: requires controlUrl AND in_progress status
  // For Twilio: only requires in_progress status (no controlUrl needed)
  const canEndCall =
    voiceProvider === VoiceAIProvider.Twilio
      ? callStatus === CallStatus.InProgress
      : controlUrl !== null && callStatus === CallStatus.InProgress;

  // Debug logging for button state
  useEffect(() => {
    console.log('[Project Detail] Button state:', {
      activeCallId,
      callStatus,
      controlUrl,
      canEndCall,
      listenUrl,
    });
  }, [activeCallId, callStatus, controlUrl, canEndCall, listenUrl]);

  const isValid = phoneNumber ? isValidPhoneNumber(phoneNumber) : false;

  const handleDownload = async (
    fileId: string,
    filename: string,
    contentType: string,
  ) => {
    try {
      setDownloadingFileId(fileId);
      await downloadFile(fileId, filename, contentType);
    } catch (error) {
      console.error('Failed to download file:', error);
    } finally {
      setDownloadingFileId(null);
    }
  };

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

  // Restore active call state on mount and update status when polling
  useEffect(() => {
    if (activeCall && activeCall.project_id === projectId) {
      // Active call matches current project - restore/update state
      console.log('[Project Detail] Restoring active call state:', activeCall);
      setActiveCallId(activeCall.call_id);
      setCallStatus(activeCall.status ?? null);
      setListenUrl(activeCall.listen_url ?? null);

      // Extract control URL from provider_data
      // TypeScript uses camelCase (auto-converted by OpenAPI generator from Python snake_case)
      const providerData = activeCall.provider_data;
      const newControlUrl = providerData?.monitor?.controlUrl;
      if (newControlUrl) {
        console.log(
          '[Project Detail] Setting control URL from polling:',
          newControlUrl,
        );
        setControlUrl(newControlUrl);
      } else {
        console.log(
          '[Project Detail] No control URL found in provider_data:',
          providerData,
        );
      }
    } else if (activeCall && activeCall.project_id !== projectId) {
      // Active call for different project - show warning
      console.log(
        '[Project Detail] Active call exists for different project:',
        activeCall.project_id,
      );
      // TODO: Show toast/notification to user about active call on different project
    }
  }, [activeCall, projectId]);

  // Store call ID and status when call starts successfully
  useEffect(() => {
    if (callAndWritetoCrmMutation.isSuccess && callAndWritetoCrmMutation.data) {
      console.log(
        '[Project Detail] Call mutation successful:',
        callAndWritetoCrmMutation.data,
      );
      setActiveCallId(callAndWritetoCrmMutation.data.call_id);
      setCallStatus(callAndWritetoCrmMutation.data.status);

      // Extract listenUrl and controlUrl from provider_data
      // TypeScript uses camelCase (auto-converted by OpenAPI generator from Python snake_case)
      const providerData = callAndWritetoCrmMutation.data.provider_data;
      if (providerData?.monitor?.listenUrl) {
        console.log(
          '[Project Detail] Setting listen URL from mutation:',
          providerData.monitor.listenUrl,
        );
        setListenUrl(providerData.monitor.listenUrl);
      }
      if (providerData?.monitor?.controlUrl) {
        console.log(
          '[Project Detail] Setting control URL from mutation:',
          providerData.monitor.controlUrl,
        );
        setControlUrl(providerData.monitor.controlUrl);
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
            The project you&apos;re looking for doesn&apos;t exist or has been
            removed.
          </p>
        </div>
      </div>
    );
  }

  const handleStartCall = async (): Promise<void> => {
    if (!phoneNumber || !isValid) {
      return;
    }

    // Resume audio context before initiating call (required for browser audio)
    // This is a no-op if Twilio isn't configured (e.g., Vapi provider)
    await resumeAudio();

    const companyName = localStorage.getItem('companyName') || undefined;

    callAndWritetoCrmMutation.mutate({
      phone_number: phoneNumber,
      // Pass customer details from project data
      customer_id: project.id,
      customer_name: project.customer_name || providerData?.customerName,
      company_name: companyName,
      customer_address: project.address_line1
        ? [
            project.address_line1,
            project.address_line2,
            [project.city, project.state].filter(Boolean).join(', '),
            project.postal_code,
            project.country,
          ]
            .filter(Boolean)
            .join(', ')
        : providerData?.address,
      claim_number: project.claim_number || providerData?.claimNumber,
      date_of_loss: project.date_of_loss,
      insurance_agency:
        project.insurance_company || providerData?.insuranceAgency,
      adjuster_name: project.adjuster_name || providerData?.adjusterName,
      adjuster_phone:
        project.adjuster_phone || providerData?.adjusterContact?.phone,
      tenant: providerData?.tenant,
      // For flat CRMs (Mock, JobNimbus), use project.id as the job_id
      // For hierarchical CRMs (Service Titan), this would need to be the actual job_id
      job_id: project.id,
    });
  };

  const handleEndCall = (): void => {
    if (!activeCallId) return;

    endCallMutation.mutate(activeCallId, {
      onSuccess: () => {
        setActiveCallId(null);
        setListenUrl(null);
        callAndWritetoCrmMutation.reset();
      },
    });
  };

  return (
    <div className="bg-white p-6">
      <div className="w-full max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column: Project Details */}
        <div className="space-y-6">
          <Card className="w-full flex flex-col max-h-[calc(100vh-12rem)]">
            <CardHeader className="flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-lg bg-gradient-to-br from-orange-400 to-pink-400 flex items-center justify-center">
                  <Building2 className="size-6 text-white" />
                </div>
                <div className="flex-1">
                  <CardTitle className="text-2xl">
                    {project.customer_name ||
                      providerData?.customerName ||
                      'Customer Name'}
                  </CardTitle>
                </div>
                {project.status && (
                  <div
                    className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getStatusColor(project.status)}`}
                  >
                    {project.status}
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-6 overflow-y-auto flex-1 min-h-0">
              {/* Customer Information */}
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <MapPin className="size-5 text-gray-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-medium text-gray-700">Address</p>
                    <div className="text-gray-600">
                      {project.address_line1 ? (
                        <>
                          <p>{project.address_line1}</p>
                          {project.address_line2 && (
                            <p>{project.address_line2}</p>
                          )}
                          <p>
                            {[project.city, project.state]
                              .filter(Boolean)
                              .join(', ')}
                            {project.postal_code && ` ${project.postal_code}`}
                          </p>
                          {project.country && <p>{project.country}</p>}
                        </>
                      ) : (
                        <p>{providerData?.address || 'Not available'}</p>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <Phone className="size-5 text-gray-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-medium text-gray-700">Phone</p>
                    <p className="text-gray-600">
                      {formatPhoneNumber(
                        providerData?.customer_phone || providerData?.phone,
                      )}
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <Mail className="size-5 text-gray-400 mt-0.5 shrink-0" />
                  <div>
                    <p className="font-medium text-gray-700">Email</p>
                    <p className="text-gray-600 break-all">
                      {providerData?.customer_email ||
                        providerData?.email ||
                        'Not available'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Claim Information */}
              {(project.claim_number ||
                project.date_of_loss ||
                project.insurance_company) && (
                <div className="border-t pt-6 space-y-4">
                  <div className="flex items-start gap-3">
                    <FileText className="size-5 text-gray-400 mt-0.5 shrink-0" />
                    <div className="flex-1 space-y-3">
                      {project.claim_number && (
                        <div>
                          <p className="font-medium text-gray-700">
                            Claim Number
                          </p>
                          <p className="text-gray-600">
                            {project.claim_number}
                          </p>
                        </div>
                      )}
                      {project.date_of_loss && (
                        <div>
                          <p className="font-medium text-gray-700">
                            Date of Loss
                          </p>
                          <p className="text-gray-600">
                            {new Date(project.date_of_loss).toLocaleDateString(
                              'en-US',
                              {
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric',
                              },
                            )}
                          </p>
                        </div>
                      )}
                      {project.insurance_company && (
                        <div>
                          <p className="font-medium text-gray-700">
                            Insurance Company
                          </p>
                          <p className="text-gray-600">
                            {project.insurance_company}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Notes */}
              {project.notes && project.notes.length > 0 && (
                <div className="border-t pt-6">
                  <p className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
                    Notes
                  </p>
                  <div className="space-y-4">
                    {[...project.notes]
                      .sort(
                        (a, b) =>
                          new Date(b.created_at).getTime() -
                          new Date(a.created_at).getTime(),
                      )
                      .map((note) => (
                        <div
                          key={note.id}
                          className="bg-gray-50 rounded-lg p-4 border border-gray-200"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2 text-sm text-gray-600">
                              <User className="size-4" />
                              <span className="font-medium">
                                {note.created_by_name || 'Unknown'}
                              </span>
                            </div>
                            <time className="text-xs text-gray-500">
                              {new Date(note.created_at).toLocaleString()}
                            </time>
                          </div>
                          <p className="text-gray-700 whitespace-pre-wrap">
                            {note.text}
                          </p>
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {project.notes && project.notes.length === 0 && (
                <div className="border-t pt-6">
                  <p className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
                    Notes
                  </p>
                  <p className="text-gray-500 text-sm pl-2">No notes yet</p>
                </div>
              )}

              {/* Files & Attachments */}
              {filesLoading && (
                <div className="border-t pt-6">
                  <p className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
                    Files & Attachments
                  </p>
                  <div className="flex items-center gap-2 text-gray-500 text-sm pl-2">
                    <Loader2 className="size-4 animate-spin" />
                    <span>Loading files...</span>
                  </div>
                </div>
              )}

              {!filesLoading && files && files.length > 0 && (
                <div className="border-t pt-6">
                  <p className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
                    Files & Attachments
                  </p>
                  <div className="space-y-3">
                    {files.map((file) => (
                      <div
                        key={file.id}
                        className="flex items-center justify-between bg-gray-50 rounded-lg p-4 border border-gray-200 hover:bg-gray-100 transition-colors"
                      >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <FileText className="size-5 text-gray-400 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {file.filename}
                            </p>
                            <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                              <span className="capitalize">
                                {file.record_type_name}
                              </span>
                              <span>•</span>
                              <span>{(file.size / 1024).toFixed(1)} KB</span>
                              <span>•</span>
                              <span>
                                {new Date(
                                  file.date_created * 1000,
                                ).toLocaleDateString()}
                              </span>
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={() =>
                            handleDownload(
                              file.id,
                              file.filename,
                              file.content_type,
                            )
                          }
                          disabled={downloadingFileId === file.id}
                          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-200 rounded-md transition-colors flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {downloadingFileId === file.id ? (
                            <>
                              <Loader2 className="size-4 animate-spin" />
                              <span>Downloading...</span>
                            </>
                          ) : (
                            <>
                              <Download className="size-4" />
                              <span>Download</span>
                            </>
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!filesLoading && files && files.length === 0 && (
                <div className="border-t pt-6">
                  <p className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
                    Files & Attachments
                  </p>
                  <p className="text-gray-500 text-sm pl-2">
                    No files attached
                  </p>
                </div>
              )}

              {/* Adjuster Contact */}
              {(project.adjuster_name ||
                project.adjuster_phone ||
                project.adjuster_email) && (
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
                        <p className="text-gray-600">
                          {formatPhoneNumber(project.adjuster_phone)}
                        </p>
                      </div>
                    )}
                    {project.adjuster_email && (
                      <div className="flex items-center gap-3">
                        <Mail className="size-4 text-gray-400" />
                        <p className="text-gray-600 break-all">
                          {project.adjuster_email}
                        </p>
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
                  <p className="text-sm text-gray-600">
                    Let your AI Assistant check on a claim.
                  </p>
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

              {/* Call Status Message */}
              {activeCallId && callStatus && (
                <div
                  className={`flex items-start gap-3 rounded-lg p-4 ${
                    callStatus === CallStatus.InProgress
                      ? 'bg-green-50 border border-green-200'
                      : callStatus === CallStatus.Ringing ||
                          callStatus === CallStatus.Queued
                        ? 'bg-blue-50 border border-blue-200'
                        : 'bg-gray-50 border border-gray-200'
                  }`}
                >
                  {callStatus === CallStatus.InProgress ? (
                    <PhoneCall className="size-5 text-green-600 mt-0.5 animate-pulse" />
                  ) : callStatus === CallStatus.Ringing ? (
                    <Loader2 className="size-5 text-blue-600 mt-0.5 animate-spin" />
                  ) : callStatus === CallStatus.Queued ? (
                    <Clock className="size-5 text-blue-600 mt-0.5" />
                  ) : (
                    <CheckCircle2 className="size-5 text-gray-600 mt-0.5" />
                  )}
                  <div className="flex-1 space-y-1">
                    <p
                      className={`text-sm font-medium ${
                        callStatus === CallStatus.InProgress
                          ? 'text-green-900'
                          : callStatus === CallStatus.Ringing ||
                              callStatus === CallStatus.Queued
                            ? 'text-blue-900'
                            : 'text-gray-900'
                      }`}
                    >
                      {callStatus === CallStatus.Queued && 'Call queued'}
                      {callStatus === CallStatus.Ringing && 'Call ringing...'}
                      {callStatus === CallStatus.InProgress &&
                        'Call in progress'}
                      {callStatus !== CallStatus.Queued &&
                        callStatus !== CallStatus.Ringing &&
                        callStatus !== CallStatus.InProgress &&
                        'Call started'}
                    </p>
                    <p
                      className={`text-xs ${
                        callStatus === CallStatus.InProgress
                          ? 'text-green-700'
                          : callStatus === CallStatus.Ringing ||
                              callStatus === CallStatus.Queued
                            ? 'text-blue-700'
                            : 'text-gray-700'
                      }`}
                    >
                      {callStatus === CallStatus.Queued &&
                        'Waiting in queue...'}
                      {callStatus === CallStatus.Ringing &&
                        'Waiting for answer...'}
                      {callStatus === CallStatus.InProgress &&
                        'Connected - You can now listen to the call'}
                      {callStatus !== CallStatus.Queued &&
                        callStatus !== CallStatus.Ringing &&
                        callStatus !== CallStatus.InProgress &&
                        callStatus &&
                        `Status: ${callStatus}`}
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
                      {callAndWritetoCrmMutation.error?.message ||
                        'An unexpected error occurred'}
                    </p>
                  </div>
                </div>
              )}

              <Button
                onClick={activeCallId ? handleEndCall : handleStartCall}
                className="w-full"
                size="lg"
                variant={activeCallId ? 'destructive' : 'default'}
                disabled={
                  activeCallId
                    ? endCallMutation.isPending || !canEndCall
                    : callAndWritetoCrmMutation.isPending ||
                      !phoneNumber ||
                      !isValid
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
                ) : callAndWritetoCrmMutation.isPending ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Creating Call...
                  </>
                ) : (
                  `Start Call with ${providerData?.insuranceAgencyContact?.name || 'Contact'}`
                )}
              </Button>

              {/* CallAudioVisualizer - Only show for Vapi */}
              {voiceProvider === VoiceAIProvider.Vapi && (
                <CallAudioVisualizer
                  listenUrl={listenUrl}
                  callStatus={callStatus}
                  onDisconnect={() => setListenUrl(null)}
                />
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
