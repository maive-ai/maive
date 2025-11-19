import { createFileRoute, useNavigate } from '@tanstack/react-router';
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Eye,
  FileSearch,
  Search,
} from 'lucide-react';
import { useState } from 'react';

import { useAddToCallList, useCallList } from '@/clients/callList';
import { useFetchProjects } from '@/clients/crm';
import {
  useAddProjectsToGroup,
  useScheduledGroups,
} from '@/clients/scheduledGroups';
import { CallListSheet } from '@/components/CallListSheet';
import { ProjectCard } from '@/components/ProjectCard';
import { ScheduledGroupModal } from '@/components/ScheduledGroupModal';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { env } from '@/env';
import { useProjectSearch } from '@/hooks/useProjectSearch';

export const Route = createFileRoute('/_authed/projects')({
  component: Projects,
});

function Projects() {
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(50);
  const { data, isLoading, isError, error } = useFetchProjects(page, pageSize);
  const { data: callListData } = useCallList();
  const { data: scheduledGroupsData } = useScheduledGroups();
  const addToCallList = useAddToCallList();
  const addProjectsToGroup = useAddProjectsToGroup();
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isSelectMode, setIsSelectMode] = useState<boolean>(false);
  const [selectedProjectIds, setSelectedProjectIds] = useState<Set<string>>(
    new Set(),
  );
  const [isCallListOpen, setIsCallListOpen] = useState<boolean>(false);
  const [isScheduleGroupModalOpen, setIsScheduleGroupModalOpen] =
    useState<boolean>(false);
  const [scheduleGroupSelectValue, setScheduleGroupSelectValue] =
    useState<string>('');
  const navigate = useNavigate();

  const handleProjectClick = (projectId: string): void => {
    navigate({ to: '/project-detail', search: { projectId } });
  };

  const toggleSelectMode = (): void => {
    setIsSelectMode(!isSelectMode);
    if (isSelectMode) {
      // Exiting select mode, clear selections
      setSelectedProjectIds(new Set());
    }
  };

  const toggleProjectSelection = (projectId: string): void => {
    setSelectedProjectIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(projectId)) {
        newSet.delete(projectId);
      } else {
        newSet.add(projectId);
      }
      return newSet;
    });
  };

  const handleAddToCallList = (): void => {
    const projectIds = Array.from(selectedProjectIds);
    // Call API to add selected projects to call list
    addToCallList.mutate(projectIds, {
      onSuccess: () => {
        // Open the call list sheet
        setIsCallListOpen(true);
        // Exit select mode and clear selections
        setIsSelectMode(false);
        setSelectedProjectIds(new Set());
      },
    });
  };

  const handleAddToScheduleGroup = async (
    groupId: number | 'new',
  ): Promise<void> => {
    const projectIds = Array.from(selectedProjectIds);

    if (groupId === 'new') {
      // Open create modal, and after creation, add projects
      setIsScheduleGroupModalOpen(true);
      // Store projectIds to add after group creation
      // We'll handle this in the modal's onSuccess callback
    } else {
      // Add to existing group
      await addProjectsToGroup.mutateAsync({ groupId, projectIds });
      // Exit select mode and clear selections
      setIsSelectMode(false);
      setSelectedProjectIds(new Set());
    }
  };

  const handleGroupCreated = async (groupId: number): Promise<void> => {
    // After group is created, add the selected projects
    const projectIds = Array.from(selectedProjectIds);
    if (projectIds.length > 0) {
      await addProjectsToGroup.mutateAsync({ groupId, projectIds });
    }
    setIsScheduleGroupModalOpen(false);
    setIsSelectMode(false);
    setSelectedProjectIds(new Set());
  };

  // Filter projects based on search query
  const filteredProjects = useProjectSearch(data?.projects, searchQuery);

  // Loading State
  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
          <p className="text-gray-600 mt-1">Loading your projects...</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6 space-y-4">
                <div className="h-10 bg-gray-200 rounded" />
                <div className="space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-3/4" />
                  <div className="h-4 bg-gray-200 rounded w-1/2" />
                  <div className="h-4 bg-gray-200 rounded w-2/3" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // Error State
  if (isError) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
        </div>
        <div className="flex flex-col items-center justify-center py-12">
          <div className="rounded-full bg-red-100 p-4 mb-4">
            <AlertCircle className="size-8 text-red-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Failed to load projects
          </h2>
          <p className="text-gray-600 text-center max-w-md">
            {error?.message ||
              'An unexpected error occurred while fetching projects.'}
          </p>
        </div>
      </div>
    );
  }

  // Empty State
  if (!data || data.projects.length === 0) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
          <p className="text-gray-600 mt-1">
            {data ? `${data.total_count} projects` : 'No projects found'}
          </p>
        </div>
        <div className="flex flex-col items-center justify-center py-12">
          <div className="rounded-full bg-gray-100 p-4 mb-4">
            <FileSearch className="size-8 text-gray-400" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            No projects found
          </h2>
          <p className="text-gray-600 text-center max-w-md">
            There are currently no projects in your CRM system.
          </p>
        </div>
      </div>
    );
  }

  // Success State with Projects Grid
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
      </div>

      {/* Action Buttons - Above Search Bar */}
      <div className="mb-4 flex justify-end gap-2">
        {/* View Call List button - shown when call list has items */}
        {env.PUBLIC_ENABLE_CALL_LIST &&
          !isSelectMode &&
          callListData &&
          callListData.total > 0 && (
            <Button onClick={() => setIsCallListOpen(true)}>
              <Eye />
              Call List
            </Button>
          )}

        {/* Add to Call List button - shown in select mode when items are selected */}
        {env.PUBLIC_ENABLE_CALL_LIST &&
          isSelectMode &&
          selectedProjectIds.size > 0 && (
            <Button
              onClick={handleAddToCallList}
              disabled={addToCallList.isPending}
            >
              {addToCallList.isPending
                ? 'Adding...'
                : `Add to Call List (${selectedProjectIds.size})`}
            </Button>
          )}

        {/* Add to Schedule Group dropdown - shown in select mode when items are selected */}
        {isSelectMode && selectedProjectIds.size > 0 && (
          <Select
            value={scheduleGroupSelectValue}
            onValueChange={(value) => {
              setScheduleGroupSelectValue('');
              if (value === 'new') {
                handleAddToScheduleGroup('new');
              } else if (value) {
                handleAddToScheduleGroup(parseInt(value, 10));
              }
            }}
          >
            <SelectTrigger className="w-[200px] bg-primary text-primary-foreground hover:bg-primary/90 border-0 data-[placeholder]:text-primary-foreground [&_svg]:text-primary-foreground [&_svg]:opacity-100 [&_svg:not([class*='text-'])]:text-primary-foreground *:data-[slot=select-value]:text-primary-foreground cursor-pointer">
              <SelectValue placeholder="Add to Schedule Group" />
            </SelectTrigger>
            <SelectContent>
              {scheduledGroupsData?.groups.length === 0 ? (
                <SelectItem value="new" className="cursor-pointer">
                  Create New Group...
                </SelectItem>
              ) : (
                <>
                  {scheduledGroupsData?.groups.map((group) => (
                    <SelectItem
                      key={group.id}
                      value={group.id.toString()}
                      className="cursor-pointer"
                    >
                      {group.name} ({group.member_count})
                    </SelectItem>
                  ))}
                  <SelectItem value="new" className="cursor-pointer">
                    Create New Group...
                  </SelectItem>
                </>
              )}
            </SelectContent>
          </Select>
        )}

        {/* Select / Cancel button */}
        <Button variant="outline" onClick={toggleSelectMode}>
          {isSelectMode ? 'Cancel' : 'Select'}
        </Button>
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-gray-400" />
          <Input
            type="text"
            placeholder="Search by name, address, phone, or claim number..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 h-12 text-base"
          />
        </div>
        {searchQuery && (
          <p className="text-sm text-gray-600 mt-2">
            {filteredProjects.length}{' '}
            {filteredProjects.length === 1 ? 'result' : 'results'} found on this
            page
            {data && ` (${data.total_count} total projects)`}
          </p>
        )}
      </div>

      {/* No Results State */}
      {searchQuery && filteredProjects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="rounded-full bg-gray-100 p-4 mb-4">
            <FileSearch className="size-8 text-gray-400" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            No results found
          </h2>
          <p className="text-gray-600 text-center max-w-md">
            No projects match your search query &ldquo;{searchQuery}&rdquo;. Try
            a different search term.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProjects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onClick={handleProjectClick}
                isSelectMode={isSelectMode}
                isSelected={selectedProjectIds.has(project.id)}
                onSelect={toggleProjectSelection}
              />
            ))}
          </div>

          {/* Pagination Controls */}
          {data && (
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="text-sm text-gray-600">
                {searchQuery ? (
                  <>
                    Showing {filteredProjects.length}{' '}
                    {filteredProjects.length === 1 ? 'result' : 'results'} on
                    page {page} of {Math.ceil(data.total_count / pageSize) || 1}
                  </>
                ) : (
                  <>
                    Showing {(page - 1) * pageSize + 1} to{' '}
                    {Math.min(page * pageSize, data.total_count)} of{' '}
                    {data.total_count} projects
                  </>
                )}
              </div>

              <div className="flex items-center gap-4">
                {/* Page Size Selector */}
                <div className="flex items-center gap-2">
                  <label htmlFor="page-size" className="text-sm text-gray-600">
                    Show:
                  </label>
                  <Select
                    value={pageSize.toString()}
                    onValueChange={(value) => {
                      setPageSize(Number(value));
                      setPage(1); // Reset to first page when changing page size
                    }}
                  >
                    <SelectTrigger id="page-size" className="w-20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="10">10</SelectItem>
                      <SelectItem value="25">25</SelectItem>
                      <SelectItem value="50">50</SelectItem>
                      <SelectItem value="100">100</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Pagination Buttons */}
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1 || isLoading}
                  >
                    <ChevronLeft className="size-4" />
                    Previous
                  </Button>

                  <div className="text-sm text-gray-600 px-2">
                    Page {page} of {Math.ceil(data.total_count / pageSize) || 1}
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => p + 1)}
                    disabled={!data.has_more || isLoading}
                  >
                    Next
                    <ChevronRight className="size-4" />
                  </Button>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Call List Sheet */}
      {env.PUBLIC_ENABLE_CALL_LIST && (
        <CallListSheet open={isCallListOpen} onOpenChange={setIsCallListOpen} />
      )}

      {/* Schedule Group Modal */}
      {isScheduleGroupModalOpen && (
        <ScheduledGroupModal
          open={isScheduleGroupModalOpen}
          onOpenChange={(open) => {
            setIsScheduleGroupModalOpen(open);
          }}
          onSuccess={handleGroupCreated}
        />
      )}
    </div>
  );
}
