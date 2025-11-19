import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { CheckCircle2, ChevronDown, ChevronUp, Edit, Play, Plus, Square, X } from 'lucide-react';
import { useState } from 'react';

import { useFetchProjects } from '@/clients/crm';
import {
  useDeleteScheduledGroup,
  useRemoveProjectFromGroup,
  useScheduledGroupDetail,
  useScheduledGroups,
  useToggleGroupActive,
  type ScheduledGroupResponse,
} from '@/clients/scheduledGroups';
import { ScheduledGroupModal } from '@/components/ScheduledGroupModal';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';
import {
  formatFrequency,
  formatGoalType,
  formatWhoToCall,
  timeToInputFormat,
} from '@/lib/scheduledGroupsUtils';
import { formatPhoneNumber, getStatusColor, getAdjusterInfo } from '@/lib/utils';

export const Route = createFileRoute('/_authed/schedule')({
  component: Schedule,
});

function Schedule() {
  const { data, isLoading } = useScheduledGroups();
  const { data: projectsData } = useFetchProjects();
  const deleteGroup = useDeleteScheduledGroup();
  const toggleActive = useToggleGroupActive();
  const removeProject = useRemoveProjectFromGroup();
  const [expandedGroups, setExpandedGroups] = useState<Set<number>>(new Set());
  const [editingGroup, setEditingGroup] = useState<ScheduledGroupResponse | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const projects = projectsData?.projects || [];
  const projectMap = new Map(projects.map((p) => [p.id, p]));

  const toggleGroupExpanded = (groupId: number): void => {
    setExpandedGroups((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(groupId)) {
        newSet.delete(groupId);
      } else {
        newSet.add(groupId);
      }
      return newSet;
    });
  };

  const handleDeleteGroup = async (groupId: number): Promise<void> => {
    if (confirm('Are you sure you want to delete this group?')) {
      await deleteGroup.mutateAsync(groupId);
    }
  };

  const handleToggleActive = async (groupId: number, isActive: boolean): Promise<void> => {
    await toggleActive.mutateAsync({ groupId, isActive });
  };

  const handleRemoveProject = async (groupId: number, projectId: string): Promise<void> => {
    await removeProject.mutateAsync({ groupId, projectId });
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-center py-12">
          <Spinner className="size-8 text-gray-400" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Schedule</h1>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="size-4 mr-2" />
          Create Group
        </Button>
      </div>

      {!data || data.groups.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12">
          <p className="text-gray-500 text-lg mb-4">No scheduled groups yet</p>
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="size-4 mr-2" />
            Create Your First Group
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {data.groups.map((group) => {
            const isExpanded = expandedGroups.has(group.id);
            return (
              <GroupCard
                key={group.id}
                group={group}
                isExpanded={isExpanded}
                onToggleExpanded={() => toggleGroupExpanded(group.id)}
                onEdit={() => setEditingGroup(group)}
                onDelete={() => handleDeleteGroup(group.id)}
                onToggleActive={() => handleToggleActive(group.id, !group.is_active)}
                onRemoveProject={(projectId) => handleRemoveProject(group.id, projectId)}
                projectMap={projectMap}
              />
            );
          })}
        </div>
      )}

      {/* Create/Edit Modal */}
      {(isCreateModalOpen || editingGroup) && (
        <ScheduledGroupModal
          open={isCreateModalOpen || editingGroup !== null}
          onOpenChange={(open) => {
            if (!open) {
              setIsCreateModalOpen(false);
              setEditingGroup(null);
            }
          }}
          group={editingGroup || undefined}
        />
      )}
    </div>
  );
}

interface GroupCardProps {
  group: ScheduledGroupResponse;
  isExpanded: boolean;
  onToggleExpanded: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onToggleActive: () => void;
  onRemoveProject: (projectId: string) => void;
  projectMap: Map<string, any>;
}

function GroupCard({
  group,
  isExpanded,
  onToggleExpanded,
  onEdit,
  onDelete,
  onToggleActive,
  onRemoveProject,
  projectMap,
}: GroupCardProps) {
  const { data: groupDetail } = useScheduledGroupDetail(isExpanded ? group.id : null);
  const removeProject = useRemoveProjectFromGroup();
  const toggleActive = useToggleGroupActive();
  const navigate = useNavigate();

  const groupProjects = groupDetail?.members || [];
  const completedCount = groupProjects.filter((m) => m.goal_completed).length;

  return (
    <Card className="overflow-hidden">
      {/* Group Header */}
      <div
        className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={onToggleExpanded}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 flex-1">
            {isExpanded ? (
              <ChevronUp className="size-5 text-gray-400" />
            ) : (
              <ChevronDown className="size-5 text-gray-400" />
            )}
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-semibold text-gray-900">{group.name}</h3>
                {group.is_active && (
                  <Badge className="bg-green-100 text-green-800">Active</Badge>
                )}
                <Badge variant="outline">{group.member_count} projects</Badge>
                {completedCount > 0 && (
                  <Badge className="bg-blue-100 text-blue-800">
                    {completedCount} completed
                  </Badge>
                )}
              </div>
              <p className="text-sm text-gray-500 mt-1">
                {formatFrequency(group.frequency)} at {timeToInputFormat(group.time_of_day)}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            <Button
              variant="outline"
              size="sm"
              onClick={onToggleActive}
              disabled={toggleActive.isPending}
            >
              {group.is_active ? (
                <>
                  <Square className="size-4 mr-2" />
                  Stop
                </>
              ) : (
                <>
                  <Play className="size-4 mr-2" />
                  Start
                </>
              )}
            </Button>
            <Button variant="outline" size="sm" onClick={onEdit}>
              <Edit className="size-4 mr-2" />
              Edit
            </Button>
            <Button variant="outline" size="sm" onClick={onDelete} disabled={removeProject.isPending}>
              <X className="size-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t bg-gray-50 p-4">
          {/* Group Settings Summary */}
          <div className="mb-4 p-3 bg-white rounded-lg">
            <h4 className="font-semibold text-sm text-gray-700 mb-2">Group Settings</h4>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-500">Frequency:</span>{' '}
                <span className="font-medium">{formatFrequency(group.frequency)}</span>
              </div>
              <div>
                <span className="text-gray-500">Time:</span>{' '}
                <span className="font-medium">{timeToInputFormat(group.time_of_day)}</span>
              </div>
              <div>
                <span className="text-gray-500">Goal:</span>{' '}
                <span className="font-medium">{formatGoalType(group.goal_type)}</span>
              </div>
              <div>
                <span className="text-gray-500">Who to Call:</span>{' '}
                <span className="font-medium">{formatWhoToCall(group.who_to_call)}</span>
              </div>
            </div>
            {group.goal_description && (
              <div className="mt-2 text-sm">
                <span className="text-gray-500">Description:</span>{' '}
                <span className="font-medium">{group.goal_description}</span>
              </div>
            )}
          </div>

          {/* Project Members */}
          <div>
            <h4 className="font-semibold text-sm text-gray-700 mb-3">
              Projects ({groupProjects.length})
            </h4>
            {groupProjects.length === 0 ? (
              <p className="text-gray-500 text-sm">No projects in this group</p>
            ) : (
              <div className="space-y-2">
                {groupProjects.map((member) => {
                  const project = projectMap.get(member.project_id);
                  if (!project) return null;

                  const adjuster = getAdjusterInfo(project);

                  return (
                        <Card
                          key={member.id}
                          className={`p-3 cursor-pointer hover:bg-gray-50 transition-colors ${
                            member.goal_completed
                              ? 'bg-green-50 border-green-200'
                              : 'bg-white'
                          }`}
                          onClick={() => navigate({ to: '/project-detail', search: { projectId: member.project_id } })}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3 flex-1">
                              {member.goal_completed && (
                                <CheckCircle2 className="size-5 text-green-600" />
                              )}
                              <div className="flex-1">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium text-gray-900">
                                    {project.customer_name || 'Unknown'}
                                  </span>
                                  <div
                                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
                                      project.status
                                    )}`}
                                  >
                                    {project.status}
                                  </div>
                                </div>
                                <div className="text-sm text-gray-600 mt-1">
                                  <span className="font-medium">Adjuster:</span> {adjuster.name}
                                  {' • '}
                                  <span className="font-medium">Phone:</span>{' '}
                                  {formatPhoneNumber(adjuster.phone)}
                                </div>
                              </div>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                onRemoveProject(member.project_id);
                              }}
                              disabled={removeProject.isPending}
                            >
                              <X className="size-4" />
                            </Button>
                          </div>
                        </Card>
                      );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}

