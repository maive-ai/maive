import { Info, X } from 'lucide-react';
import { useState } from 'react';

import { useCallList, useRemoveFromCallList } from '@/clients/callList';
import { useFetchProjects } from '@/clients/crm';
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
import { formatPhoneNumber, getStatusColor } from '@/lib/utils';

interface CallListSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CallListSheet({ open, onOpenChange }: CallListSheetProps) {
  const { data: callListData, isLoading: isLoadingCallList } = useCallList();
  const { data: projectsData } = useFetchProjects();
  const removeFromCallList = useRemoveFromCallList();
  const [isInfoDialogOpen, setIsInfoDialogOpen] = useState(false);

  const callListItems = callListData?.items || [];
  const projects = projectsData?.projects || [];

  // Create a map of project IDs to projects for quick lookup
  const projectMap = new Map(projects.map((p) => [p.id, p]));

  const handleRemove = (projectId: string) => {
    removeFromCallList.mutate(projectId);
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

        <div className="mt-6 flex flex-col h-[calc(100vh-140px)]">
          {/* Call list items */}
          <div className="flex-1 overflow-y-auto space-y-4 px-2">
            {isLoadingCallList ? (
              <div className="flex items-center justify-center py-12">
                <p className="text-gray-500">Loading call list...</p>
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
                        className="p-1 rounded-full hover:bg-gray-100 transition-colors"
                        aria-label="Remove from call list"
                      >
                        <X className="size-4 text-gray-400 hover:text-gray-600" />
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
          <div className="pt-12 mt-12 px-4">
            <Button
              onClick={() => onOpenChange(false)}
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
