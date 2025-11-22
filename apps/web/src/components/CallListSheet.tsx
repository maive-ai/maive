import { CallStatus, VoiceAIProvider } from '@maive/api/client';
import { Home, Pause, PhoneOff, Play, ShieldCheck, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { isValidPhoneNumber } from 'react-phone-number-input';

import { useEndCall, useVoiceAIProvider } from '@/clients/ai/voice';
import { useCallList, useRemoveFromCallList } from '@/clients/callList';
import { useFetchProjects } from '@/clients/crm';
import {
  useCallAndWriteToCrm,
  useFetchProjectSummary,
} from '@/clients/workflows';
import { ExpandedCallCard } from '@/components/ExpandedCallCard';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty';
import { Item, ItemGroup, ItemHeader } from '@/components/ui/item';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { Spinner } from '@/components/ui/spinner';
import { useActiveCallPolling } from '@/hooks/useActiveCallPolling';
import { getStatusColor } from '@/lib/utils';

interface CallListSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Wrapper component that fetches project summary using TanStack Query (with caching)
 * and passes it to ExpandedCallCard
 */
function ExpandedCallCardWithSummary({
  projectId,
  ...props
}: Omit<React.ComponentProps<typeof ExpandedCallCard>, 'projectSummary'> & {
  projectId: string;
}) {
  // Fetch summary with automatic caching (2-minute stale time, 5-minute cache)
  const { data: projectSummary } = useFetchProjectSummary(projectId);

  return <ExpandedCallCard {...props} projectSummary={projectSummary} />;
}

export function CallListSheet({ open, onOpenChange }: CallListSheetProps) {
  const {
    data: callListData,
    isLoading: isLoadingCallList,
    refetch,
  } = useCallList();

  // Refetch call list when sheet opens
  useEffect(() => {
    if (open) {
      refetch();
    }
  }, [open, refetch]);
  const { data: projectsData, isLoading: isLoadingProjects } =
    useFetchProjects();
  const removeFromCallList = useRemoveFromCallList();

  // Auto-clean call list: remove items whose projects no longer exist
  useEffect(() => {
    if (callListData && projectsData && !isLoadingProjects) {
      const missingProjects = callListData.items.filter(
        (item) =>
          !projectsData.projects.some((p) => p.id === item.project_id) &&
          !cleanedProjectIds.has(item.project_id),
      );

      if (missingProjects.length > 0) {
        // Track that we're cleaning these projects
        setCleanedProjectIds(
          (prev) =>
            new Set([
              ...prev,
              ...missingProjects.map((item) => item.project_id),
            ]),
        );

        // Remove each missing project from the call list
        missingProjects.forEach((item) => {
          removeFromCallList.mutate(item.project_id);
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [callListData, projectsData, isLoadingProjects]);
  const [removingProjectId, setRemovingProjectId] = useState<string | null>(
    null,
  );
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<string | null>(null);
  const [cleanedProjectIds, setCleanedProjectIds] = useState<Set<string>>(
    new Set(),
  );

  // Power dialer state
  const [isDialerActive, setIsDialerActive] = useState(false);
  const [currentDialingIndex, setCurrentDialingIndex] = useState(0);
  const [activeCallId, setActiveCallId] = useState<string | null>(null);
  const [callStatus, setCallStatus] = useState<CallStatus | null>(null);
  const [listenUrl, setListenUrl] = useState<string | null>(null);
  const [controlUrl, setControlUrl] = useState<string | null>(null);

  // Ref to track current activeCallId for race condition prevention
  const activeCallIdRef = useRef<string | null>(null);
  // Ref to track if user manually stopped the dialer
  const userStoppedDialerRef = useRef(false);
  // Ref to track the call ID we're currently ending to prevent race conditions
  const endingCallIdRef = useRef<string | null>(null);

  // Call mutations
  const callAndWriteToCrmMutation = useCallAndWriteToCrm();
  const endCallMutation = useEndCall();

  // Check voice AI provider (Twilio vs Vapi)
  const { data: voiceProvider } = useVoiceAIProvider();

  const callListItems = useMemo(
    () => callListData?.items || [],
    [callListData?.items],
  );
  const projects = useMemo(
    () => projectsData?.projects || [],
    [projectsData?.projects],
  );

  // Create a map of project IDs to projects for quick lookup
  const projectMap = useMemo(
    () => new Map(projects.map((p) => [p.id, p])),
    [projects],
  );

  const handleRemove = (projectId: string) => {
    setProjectToDelete(projectId);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (projectToDelete) {
      setRemovingProjectId(projectToDelete);
      removeFromCallList.mutate(projectToDelete);
      setDeleteDialogOpen(false);
      setProjectToDelete(null);
    }
  };

  // Poll for active call status
  const { data: activeCall } = useActiveCallPolling({
    onCallEnded: () => {
      setActiveCallId(null);
      setCallStatus(null);
      setListenUrl(null);
      setControlUrl(null);
      callAndWriteToCrmMutation.reset();

      // Auto-advance to next contact
      if (isDialerActive) {
        const nextIndex = currentDialingIndex + 1;
        if (nextIndex < callListItems.length) {
          setCurrentDialingIndex(nextIndex);
          // Initiate next call after a brief delay
          setTimeout(() => {
            initiateCall(nextIndex);
          }, 1000);
        } else {
          // End of list - stop dialer
          setIsDialerActive(false);
          setCurrentDialingIndex(0);
        }
      }
    },
  });

  // Determine if we can end the call
  // For Vapi: requires controlUrl AND in_progress status
  // For Twilio: only requires in_progress status (no controlUrl needed)
  const canEndCall =
    voiceProvider === VoiceAIProvider.Twilio
      ? callStatus === CallStatus.InProgress
      : controlUrl !== null && callStatus === CallStatus.InProgress;

  // Clear removing state when the item is actually gone from the list
  useEffect(() => {
    if (
      removingProjectId &&
      !callListItems.some((item) => item.project_id === removingProjectId)
    ) {
      setRemovingProjectId(null);
    }
  }, [removingProjectId, callListItems]);

  // Keep ref in sync with state
  useEffect(() => {
    activeCallIdRef.current = activeCallId;
  }, [activeCallId]);

  // Restore active call state on mount and update status when polling
  useEffect(() => {
    if (activeCall) {
      setActiveCallId(activeCall.call_id);
      setCallStatus(activeCall.status ?? null);
      setListenUrl(activeCall.listen_url ?? null);

      // Extract control URL from provider_data
      const providerData = activeCall.provider_data;
      const newControlUrl = providerData?.monitor?.controlUrl;
      if (newControlUrl) {
        setControlUrl(newControlUrl);
      }

      // If we have an active call, find which project it belongs to and set that as current
      const callProjectIndex = callListItems.findIndex(
        (item) => item.project_id === activeCall.project_id,
      );
      if (callProjectIndex !== -1) {
        setCurrentDialingIndex(callProjectIndex);
        // Only restore dialer state if user hasn't manually stopped it
        // This prevents polling from reactivating the dialer after user clicks "Stop"
        if (!userStoppedDialerRef.current) {
          setIsDialerActive(true);
        }
      }
    }
  }, [activeCall, callListItems]);

  // Store call ID and status when call starts successfully
  useEffect(() => {
    if (callAndWriteToCrmMutation.isSuccess && callAndWriteToCrmMutation.data) {
      const newCallId = callAndWriteToCrmMutation.data.call_id;
      setActiveCallId(newCallId);
      setCallStatus(callAndWriteToCrmMutation.data.status);

      // Extract listenUrl and controlUrl from provider_data
      const providerData = callAndWriteToCrmMutation.data.provider_data;
      if (providerData?.monitor?.listenUrl) {
        setListenUrl(providerData.monitor.listenUrl);
      }
      if (providerData?.monitor?.controlUrl) {
        setControlUrl(providerData.monitor.controlUrl);
      }

      // Clear any pending end call ref to prevent race conditions
      // This ensures that if a new call starts while an old end call mutation is pending,
      // the old mutation won't clear the new call's state
      endingCallIdRef.current = null;
    }
  }, [callAndWriteToCrmMutation.isSuccess, callAndWriteToCrmMutation.data]);

  // Function to initiate a call for a given index
  const initiateCall = (index: number) => {
    const item = callListItems[index];
    if (!item) return;

    const project = projectMap.get(item.project_id);
    if (!project) return;

    // Extract adjuster info from provider_data
    const providerData = project.provider_data as any;
    let adjusterPhone =
      project.adjuster_phone ||
      providerData?.adjusterPhone ||
      providerData?.adjusterContact?.phone;

    // Validate phone number
    if (!adjusterPhone) {
      // Skip to next contact
      const nextIndex = index + 1;
      if (nextIndex < callListItems.length) {
        setCurrentDialingIndex(nextIndex);
        setTimeout(() => initiateCall(nextIndex), 500);
      } else {
        setIsDialerActive(false);
      }
      return;
    }

    // Ensure phone number is in E.164 format
    if (!adjusterPhone.startsWith('+')) {
      adjusterPhone = '+1' + adjusterPhone.replace(/\D/g, '');
    }

    // Validate phone number format
    if (!isValidPhoneNumber(adjusterPhone)) {
      // Skip to next contact
      const nextIndex = index + 1;
      if (nextIndex < callListItems.length) {
        setCurrentDialingIndex(nextIndex);
        setTimeout(() => initiateCall(nextIndex), 500);
      } else {
        setIsDialerActive(false);
      }
      return;
    }

    const companyName = localStorage.getItem('companyName') || undefined;

    callAndWriteToCrmMutation.mutate({
      phone_number: adjusterPhone,
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
      adjuster_name:
        project.adjuster_name ||
        providerData?.adjusterName ||
        providerData?.adjusterContact?.name,
      adjuster_phone: adjusterPhone,
      tenant: providerData?.tenant,
      job_id: project.id,
    });
  };

  const handleToggleDialer = () => {
    if (isDialerActive) {
      // Stop dialing
      setIsDialerActive(false);
      userStoppedDialerRef.current = true; // Track that user manually stopped
      // If there's an active call, end it
      if (activeCallId && canEndCall) {
        handleEndCall();
      }
    } else {
      // Start dialing from the beginning
      setIsDialerActive(true);
      userStoppedDialerRef.current = false; // Clear manual stop flag
      // Clear any pending end call ref to prevent race conditions
      endingCallIdRef.current = null;
      setCurrentDialingIndex(0);
      initiateCall(0);
    }
  };

  const handleEndCall = () => {
    if (!activeCallId) return;

    // Store the call ID we're ending to prevent race conditions
    const callIdToEnd = activeCallId;
    endingCallIdRef.current = callIdToEnd;

    endCallMutation.mutate(callIdToEnd, {
      onSuccess: () => {
        // Only clear state if:
        // 1. This is still the active call (not a new call that started)
        // 2. We're still ending this specific call (not cleared by a new call start)
        // This prevents clearing state from a new call that started after this mutation
        // If endingCallIdRef was cleared (set to null), it means a new call started
        if (
          activeCallIdRef.current === callIdToEnd &&
          endingCallIdRef.current === callIdToEnd
        ) {
          setActiveCallId(null);
          setListenUrl(null);
          setControlUrl(null);
          setCallStatus(null);
          callAndWriteToCrmMutation.reset();
        }
        // Clear the ending call ID ref if this was the call we were ending
        if (endingCallIdRef.current === callIdToEnd) {
          endingCallIdRef.current = null;
        }
      },
    });
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-[400px] sm:w-[540px] bg-white [&>button]:hidden"
      >
        {/* Centered Start Dialing button */}
        <div className="flex justify-center pt-4 pb-4">
          <Button
            onClick={handleToggleDialer}
            disabled={
              isLoadingCallList ||
              isLoadingProjects ||
              callAndWriteToCrmMutation.isPending ||
              endCallMutation.isPending ||
              callListItems.length === 0
            }
            size="sm"
            variant={isDialerActive ? 'destructive' : 'default'}
            className="gap-2"
          >
            {isDialerActive ? (
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
        </div>

        {/* Call List Title and Count - Aligned with card edges */}
        <div className="px-2 pb-3 flex items-baseline justify-between">
          <SheetTitle className="text-base font-semibold">Call List</SheetTitle>
          <p className="text-sm text-gray-500">
            {callListItems.length === 0
              ? 'No contacts'
              : isDialerActive
                ? `Calling ${currentDialingIndex + 1} of ${callListItems.length}`
                : `${callListItems.length} contact${callListItems.length !== 1 ? 's' : ''} ready`}
          </p>
        </div>

        <div className="flex flex-col h-[calc(100vh-170px)]">
          {/* Call list items */}
          <div className="flex-1 overflow-y-auto px-2">
            {isLoadingCallList || isLoadingProjects ? (
              <div className="flex flex-col items-center justify-center py-12 gap-3">
                <Spinner className="size-8 text-gray-400" />
                <p className="text-gray-500">
                  {isLoadingProjects
                    ? 'Loading projects...'
                    : 'Loading call list...'}
                </p>
              </div>
            ) : callListItems.length === 0 ? (
              <Empty>
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <PhoneOff />
                  </EmptyMedia>
                  <EmptyTitle>No contacts in call list</EmptyTitle>
                  <EmptyDescription>
                    Add projects to your call list to start making calls with
                    the power dialer.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              <ItemGroup>
                {callListItems.map((item, index) => {
                  const project = projectMap.get(item.project_id);
                  if (!project) return null;

                  // Extract adjuster info from provider_data
                  const providerData = project.provider_data as any;
                  const adjusterName =
                    project.adjuster_name ||
                    providerData?.adjusterName ||
                    providerData?.adjusterContact?.name ||
                    'No adjuster';
                  const adjusterPhone =
                    project.adjuster_phone ||
                    providerData?.adjusterPhone ||
                    providerData?.adjusterContact?.phone ||
                    'No phone';
                  const customerName =
                    project.customer_name ||
                    providerData?.customerName ||
                    'Unknown Customer';
                  const address = project.address_line1
                    ? [
                        project.address_line1,
                        project.address_line2,
                        [project.city, project.state]
                          .filter(Boolean)
                          .join(', '),
                        project.postal_code,
                      ]
                        .filter(Boolean)
                        .join(', ')
                    : providerData?.address || 'No address';

                  // Check if this is the currently active call
                  const isExpanded =
                    isDialerActive && index === currentDialingIndex;

                  return (
                    <div key={item.id} className="mb-3">
                      {isExpanded ? (
                        <ExpandedCallCardWithSummary
                          projectId={item.project_id}
                          adjusterName={adjusterName}
                          adjusterPhone={adjusterPhone}
                          customerName={customerName}
                          address={address}
                          claimNumber={
                            project.claim_number || providerData?.claimNumber
                          }
                          projectStatus={project.status}
                          callStatus={callStatus}
                          listenUrl={listenUrl}
                          canEndCall={canEndCall}
                          voiceProvider={voiceProvider}
                          onEndCall={handleEndCall}
                          isEndingCall={endCallMutation.isPending}
                        />
                      ) : (
                        <Item variant="outline" className="relative rounded-lg">
                          {/* Header with status badge and remove button */}
                          <ItemHeader>
                            <Badge
                              className={`${getStatusColor(project.status)} pointer-events-none`}
                            >
                              {project.status}
                            </Badge>
                            <button
                              onClick={() => handleRemove(item.project_id)}
                              disabled={removingProjectId === item.project_id}
                              className="p-1 rounded-full hover:bg-red-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              aria-label="Remove from call list"
                            >
                              {removingProjectId === item.project_id ? (
                                <Spinner className="size-4 text-gray-400" />
                              ) : (
                                <Trash2 className="size-4 text-gray-500 hover:text-red-600" />
                              )}
                            </button>
                          </ItemHeader>

                          {/* Main content - two columns */}
                          <div className="w-full grid grid-cols-2 gap-4 pt-2">
                            {/* Left: Homeowner */}
                            <div className="flex items-center gap-2">
                              <Home className="size-4 text-gray-400 shrink-0" />
                              <div className="min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate">
                                  {customerName}
                                </p>
                              </div>
                            </div>

                            {/* Right: Adjuster */}
                            <div className="flex items-center gap-2">
                              <ShieldCheck className="size-4 text-gray-400 shrink-0" />
                              <div className="min-w-0">
                                <p className="text-sm font-medium text-gray-900 truncate">
                                  {adjusterName}
                                </p>
                              </div>
                            </div>
                          </div>
                        </Item>
                      )}
                    </div>
                  );
                })}
              </ItemGroup>
            )}
          </div>

          {/* Actions */}
          <div className="pt-6 mt-6 px-4 space-y-4 border-t">
            <Button
              onClick={() => onOpenChange(false)}
              variant="outline"
              className="w-full"
            >
              Close
            </Button>
          </div>
        </div>
      </SheetContent>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove from call list?</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove this project from your call list. You can add it
              back later if needed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-red-600 hover:bg-red-700"
            >
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Sheet>
  );
}
