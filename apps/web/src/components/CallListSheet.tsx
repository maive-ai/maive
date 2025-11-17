import { Info, Phone, PhoneOff, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { useActiveCall, useEndCall } from '@/clients/ai/voice';
import { useCallList, useRemoveFromCallList, useMarkCallCompleted } from '@/clients/callList';
import { useFetchProjects } from '@/clients/crm';
import { useCallAndWriteToCrm } from '@/clients/workflows';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Spinner } from '@/components/ui/spinner';
import { formatPhoneNumber, getStatusColor } from '@/lib/utils';

interface CallListSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CallListSheet({ open, onOpenChange }: CallListSheetProps) {
  const { data: callListData, isLoading: isLoadingCallList } = useCallList();
  const { data: projectsData, isLoading: isLoadingProjects } = useFetchProjects();
  const { data: activeCall, isLoading: isLoadingActiveCall } = useActiveCall();
  const removeFromCallList = useRemoveFromCallList();
  const callAndWriteToCrm = useCallAndWriteToCrm();
  const endCall = useEndCall();
  const markCallCompleted = useMarkCallCompleted();
  const [isInfoDialogOpen, setIsInfoDialogOpen] = useState(false);
  const [removingProjectId, setRemovingProjectId] = useState<string | null>(null);
  const [previousCall, setPreviousCall] = useState<{ callId: string; projectId: string } | null>(null);

  const callListItems = useMemo(() => callListData?.items || [], [callListData?.items]);
  const projects = useMemo(() => projectsData?.projects || [], [projectsData?.projects]);

  // Create a map of project IDs to projects for quick lookup
  const projectMap = useMemo(() => new Map(projects.map((p) => [p.id, p])), [projects]);

  // Find the first uncompleted call
  const nextCall = useMemo(() => {
    const uncompletedItem = callListItems.find(item => !item.call_completed);
    if (!uncompletedItem) return null;

    const project = projectMap.get(uncompletedItem.project_id);
    if (!project) return null;

    // Extract adjuster info from provider_data
    const providerData = project.provider_data as any;
    const adjusterPhone =
      project.adjuster_phone ||
      providerData?.adjusterPhone ||
      providerData?.adjusterContact?.phone ||
      null;

    return {
      projectId: project.id,
      phone: adjusterPhone,
      callListItem: uncompletedItem,
    };
  }, [callListItems, projectMap]);

  const handleRemove = (projectId: string) => {
    setRemovingProjectId(projectId);
    removeFromCallList.mutate(projectId);
  };

  // Handler to start dialing the next uncompleted call
  const handleStartDialing = () => {
    if (!nextCall || !nextCall.phone) {
      console.error('[Dialer] No valid phone number for next call');
      return;
    }

    callAndWriteToCrm.mutate({
      phone_number: nextCall.phone,
      job_id: nextCall.projectId,
    });
  };

  // Handler to end the active call
  const handleEndCall = () => {
    if (!activeCall?.call_id) {
      console.error('[Dialer] No active call to end');
      return;
    }

    endCall.mutate(activeCall.call_id);
  };

  // Clear removing state when the item is actually gone from the list
  useEffect(() => {
    if (removingProjectId && !callListItems.some(item => item.project_id === removingProjectId)) {
      setRemovingProjectId(null);
    }
  }, [removingProjectId, callListItems]);

  // Detect when a call ends and mark it as completed
  useEffect(() => {
    // If there was an active call but now there isn't, the call has ended
    if (previousCall && !activeCall) {
      console.log('[Dialer] Call ended, marking project as completed:', previousCall.projectId);

      // Mark the call as completed in the call list
      markCallCompleted.mutate({
        projectId: previousCall.projectId,
        completed: true
      });

      setPreviousCall(null);
    } else if (activeCall?.call_id && activeCall.call_id !== previousCall?.callId) {
      // New call started, track it
      console.log('[Dialer] New call started:', activeCall.call_id, 'for project:', activeCall.project_id);
      setPreviousCall({
        callId: activeCall.call_id,
        projectId: activeCall.project_id
      });
    }
  }, [activeCall, previousCall, markCallCompleted]);

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

        <div className="mt-6 flex flex-col h-[calc(100vh-140px)]">
          {/* Call list items */}
          <div className="flex-1 overflow-y-auto space-y-4 px-2">
            {isLoadingCallList || isLoadingProjects ? (
              <div className="flex flex-col items-center justify-center py-12 gap-3">
                <Spinner className="size-8 text-gray-400" />
                <p className="text-gray-500">
                  {isLoadingProjects ? 'Loading projects...' : 'Loading call list...'}
                </p>
              </div>
            ) : callListItems.length === 0 ? (
              <div className="flex items-center justify-center py-12">
                <p className="text-gray-500">No projects in call list</p>
              </div>
            ) : (
              callListItems.map((item) => {
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

                return (
                  <Card key={item.id} className="p-5 shadow-sm">
                    {/* Top row: Badge and close button */}
                    <div className="flex justify-between items-center mb-2">
                      <Badge className={`${getStatusColor(project.status)} pointer-events-none`}>
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
                    </div>

                    {/* Adjuster info - horizontal layout */}
                    <div className="flex gap-6">
                      {/* Adjuster name */}
                      <div>
                        <p className="text-sm font-semibold text-gray-700">
                          Adjuster
                        </p>
                        <p className="text-sm text-gray-900">{adjusterName}</p>
                      </div>

                      {/* Adjuster phone */}
                      <div>
                        <p className="text-sm font-semibold text-gray-700">
                          Phone
                        </p>
                        <p className="text-sm text-gray-900">{formatPhoneNumber(adjusterPhone)}</p>
                      </div>
                    </div>
                  </Card>
                );
              })
            )}
          </div>

          {/* Actions */}
          <div className="pt-12 mt-12 px-4 space-y-3">
            {/* Active call controls */}
            {activeCall ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
                  <Phone className="size-4 text-green-600 animate-pulse" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-green-900">Call in progress</p>
                    <p className="text-xs text-green-700">{formatPhoneNumber(activeCall.phone_number)}</p>
                  </div>
                </div>
                <Button
                  onClick={handleEndCall}
                  disabled={endCall.isPending}
                  variant="destructive"
                  className="w-full"
                >
                  {endCall.isPending ? (
                    <>
                      <Spinner className="size-4 mr-2" />
                      Ending Call...
                    </>
                  ) : (
                    <>
                      <PhoneOff className="size-4 mr-2" />
                      End Call
                    </>
                  )}
                </Button>
              </div>
            ) : (
              /* Start dialing button */
              <Button
                onClick={handleStartDialing}
                disabled={
                  !nextCall ||
                  !nextCall.phone ||
                  callAndWriteToCrm.isPending ||
                  isLoadingCallList ||
                  isLoadingProjects
                }
                className="w-full"
              >
                {callAndWriteToCrm.isPending ? (
                  <>
                    <Spinner className="size-4 mr-2" />
                    Starting Call...
                  </>
                ) : (
                  <>
                    <Phone className="size-4 mr-2" />
                    Start Dialing
                    {nextCall && nextCall.phone && (
                      <span className="ml-2 text-xs opacity-75">
                        ({formatPhoneNumber(nextCall.phone)})
                      </span>
                    )}
                  </>
                )}
              </Button>
            )}

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

      {/* Info Dialog */}
      <Dialog open={isInfoDialogOpen} onOpenChange={setIsInfoDialogOpen}>
        <DialogContent className="bg-white">
          <DialogHeader>
            <DialogTitle>Call List Information</DialogTitle>
            <DialogDescription>
              Projects queued for batch calling
            </DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    </Sheet>
  );
}
