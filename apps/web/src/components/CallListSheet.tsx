import { Info, PhoneOff, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { isValidPhoneNumber } from 'react-phone-number-input';

import { useEndCall } from '@/clients/ai/voice';
import { useCallList, useRemoveFromCallList } from '@/clients/callList';
import { useFetchProjects } from '@/clients/crm';
import { useCallAndWriteToCrm } from '@/clients/workflows';
import { ExpandedCallCard } from '@/components/ExpandedCallCard';
import { PowerDialerControl } from '@/components/PowerDialerControl';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle
} from '@/components/ui/empty';
import {
  Item,
  ItemContent,
  ItemGroup,
  ItemHeader,
  ItemSeparator,
  ItemTitle
} from '@/components/ui/item';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle
} from '@/components/ui/sheet';
import { Spinner } from '@/components/ui/spinner';
import { useActiveCallPolling } from '@/hooks/useActiveCallPolling';
import { getStatusColor } from '@/lib/utils';

interface CallListSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CallListSheet({ open, onOpenChange }: CallListSheetProps) {
  const { data: callListData, isLoading: isLoadingCallList, refetch } =
    useCallList();

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
        (item) => !projectsData.projects.some((p) => p.id === item.project_id)
      );

      if (missingProjects.length > 0) {
        // Remove each missing project from the call list
        missingProjects.forEach((item) => {
          removeFromCallList.mutate(item.project_id);
        });
      }
    }
  }, [callListData, projectsData, isLoadingProjects, removeFromCallList]);
  const [isInfoDialogOpen, setIsInfoDialogOpen] = useState(false);
  const [removingProjectId, setRemovingProjectId] = useState<string | null>(
    null,
  );

  // Power dialer state
  const [isDialerActive, setIsDialerActive] = useState(false);
  const [currentDialingIndex, setCurrentDialingIndex] = useState(0);
  const [activeCallId, setActiveCallId] = useState<string | null>(null);
  const [callStatus, setCallStatus] = useState<string | null>(null);
  const [listenUrl, setListenUrl] = useState<string | null>(null);
  const [controlUrl, setControlUrl] = useState<string | null>(null);

  // Call mutations
  const callAndWriteToCrmMutation = useCallAndWriteToCrm();
  const endCallMutation = useEndCall();

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
    setRemovingProjectId(projectId);
    removeFromCallList.mutate(projectId);
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

  // Only allow ending the call when we have the control URL AND the call is ringing or connected
  const canEndCall = controlUrl !== null && callStatus === 'in_progress';

  // Clear removing state when the item is actually gone from the list
  useEffect(() => {
    if (
      removingProjectId &&
      !callListItems.some((item) => item.project_id === removingProjectId)
    ) {
      setRemovingProjectId(null);
    }
  }, [removingProjectId, callListItems]);

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
        setIsDialerActive(true);
      }
    }
  }, [activeCall, callListItems]);

  // Store call ID and status when call starts successfully
  useEffect(() => {
    if (callAndWriteToCrmMutation.isSuccess && callAndWriteToCrmMutation.data) {
      setActiveCallId(callAndWriteToCrmMutation.data.call_id);
      setCallStatus(callAndWriteToCrmMutation.data.status);

      // Extract listenUrl and controlUrl from provider_data
      const providerData = callAndWriteToCrmMutation.data.provider_data;
      if (providerData?.monitor?.listenUrl) {
        setListenUrl(providerData.monitor.listenUrl);
      }
      if (providerData?.monitor?.controlUrl) {
        setControlUrl(providerData.monitor.controlUrl);
      }
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
      // If there's an active call, end it
      if (activeCallId && canEndCall) {
        handleEndCall();
      }
    } else {
      // Start dialing from the beginning
      setIsDialerActive(true);
      setCurrentDialingIndex(0);
      initiateCall(0);
    }
  };

  const handleEndCall = () => {
    if (!activeCallId) return;

    endCallMutation.mutate(activeCallId, {
      onSuccess: () => {
        setActiveCallId(null);
        setListenUrl(null);
        setControlUrl(null);
        setCallStatus(null);
        callAndWriteToCrmMutation.reset();
      },
    });
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[400px] sm:w-[540px] bg-white">
        <SheetHeader className="pb-4">
          <div className="flex items-center gap-2">
            <SheetTitle>Call List</SheetTitle>
            <button
              onClick={() => setIsInfoDialogOpen(true)}
              className="p-1 rounded-full hover:bg-gray-100 transition-colors"
              aria-label="Call list information"
            >
              <Info className="size-4 text-gray-500" />
            </button>
          </div>
        </SheetHeader>

        {/* Power Dialer Control */}
        <PowerDialerControl
          isActive={isDialerActive}
          onToggle={handleToggleDialer}
          currentIndex={currentDialingIndex}
          totalContacts={callListItems.length}
          disabled={
            isLoadingCallList ||
            isLoadingProjects ||
            callAndWriteToCrmMutation.isPending
          }
        />

        <div className="mt-6 flex flex-col h-[calc(100vh-220px)]">
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
                        [project.city, project.state].filter(Boolean).join(', '),
                        project.postal_code,
                      ]
                        .filter(Boolean)
                        .join(', ')
                    : providerData?.address || 'No address';

                  // Check if this is the currently active call
                  const isExpanded =
                    isDialerActive && index === currentDialingIndex;

                  return (
                    <div key={item.id}>
                      {index > 0 && <ItemSeparator />}
                      {isExpanded ? (
                        <ExpandedCallCard
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
                          onEndCall={handleEndCall}
                          isEndingCall={endCallMutation.isPending}
                        />
                      ) : (
                        <Item variant="default" className="relative">
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
                              className="p-1 rounded-full hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                              aria-label="Remove from call list"
                            >
                              {removingProjectId === item.project_id ? (
                                <Spinner className="size-4 text-gray-400" />
                              ) : (
                                <X className="size-4 text-gray-400 hover:text-gray-600" />
                              )}
                            </button>
                          </ItemHeader>

                          {/* Main content - compact layout */}
                          <ItemContent>
                            <ItemTitle>{adjusterName}</ItemTitle>
                            <div className="text-sm text-gray-600">
                              {customerName}
                            </div>
                          </ItemContent>
                        </Item>
                      )}
                    </div>
                  );
                })}
              </ItemGroup>
            )}
          </div>

          {/* Actions */}
          <div className="pt-12 mt-12 px-4">
            <Button onClick={() => onOpenChange(false)} className="w-full">
              Close
            </Button>
          </div>
        </div>
      </SheetContent>

      {/* Info Dialog */}
      <Dialog open={isInfoDialogOpen} onOpenChange={setIsInfoDialogOpen}>
        <DialogContent className="bg-white">
          <DialogHeader>
            <DialogTitle>Call List Information</DialogTitle>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    </Sheet>
  );
}
