import { useState, useEffect } from 'react';

import {
  useCreateScheduledGroup,
  useUpdateScheduledGroup,
  type ScheduledGroupResponse,
  type GoalType,
  type WhoToCall,
} from '@/clients/scheduledGroups';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import {
  DAYS_OF_WEEK,
  GOAL_TYPE_OPTIONS,
  WHO_TO_CALL_OPTIONS,
  timeToInputFormat,
  timeToApiFormat,
} from '@/lib/scheduledGroupsUtils';

interface ScheduledGroupModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  group?: ScheduledGroupResponse;
  onSuccess?: (groupId: number) => void;
}

export function ScheduledGroupModal({
  open,
  onOpenChange,
  group,
  onSuccess,
}: ScheduledGroupModalProps) {
  const createGroup = useCreateScheduledGroup();
  const updateGroup = useUpdateScheduledGroup();

  const [name, setName] = useState('');
  const [frequency, setFrequency] = useState<string[]>([]);
  const [timeOfDay, setTimeOfDay] = useState('09:00');
  const [goalType, setGoalType] = useState<GoalType>('status_check');
  const [goalDescription, setGoalDescription] = useState('');
  const [whoToCall, setWhoToCall] = useState<WhoToCall>('adjuster');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const isEditMode = !!group;

  // Initialize form with group data when editing
  useEffect(() => {
    if (group) {
      setName(group.name);
      setFrequency(group.frequency);
      setTimeOfDay(timeToInputFormat(group.time_of_day));
      setGoalType(group.goal_type as GoalType);
      setGoalDescription(group.goal_description || '');
      setWhoToCall(group.who_to_call as WhoToCall);
    } else {
      // Reset form for create mode
      setName('');
      setFrequency([]);
      setTimeOfDay('09:00');
      setGoalType('status_check');
      setGoalDescription('');
      setWhoToCall('adjuster');
      setErrors({});
    }
  }, [group, open]);

  const toggleDay = (day: string): void => {
    setFrequency((prev) => {
      if (prev.includes(day)) {
        return prev.filter((d) => d !== day);
      } else {
        return [...prev, day];
      }
    });
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!name.trim()) {
      newErrors.name = 'Group name is required';
    }

    if (frequency.length === 0) {
      newErrors.frequency = 'Select at least one day';
    }

    if (goalType === 'user_specified' && !goalDescription.trim()) {
      newErrors.goalDescription = 'Goal description is required for user specified goals';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (): Promise<void> => {
    if (!validate()) {
      return;
    }

    try {
      const timeWithSeconds = timeToApiFormat(timeOfDay);

      if (isEditMode && group) {
        await updateGroup.mutateAsync({
          groupId: group.id,
          request: {
            name,
            frequency,
            time_of_day: timeWithSeconds,
            goal_type: goalType,
            goal_description: goalDescription || null,
            who_to_call: whoToCall,
          },
        });
        onOpenChange(false);
      } else {
        const newGroup = await createGroup.mutateAsync({
          name,
          frequency,
          time_of_day: timeWithSeconds,
          goal_type: goalType,
          goal_description: goalDescription || null,
          who_to_call: whoToCall,
        });
        // Call onSuccess callback if provided (e.g., to add projects after creation)
        if (onSuccess) {
          onSuccess(newGroup.id);
        }
        onOpenChange(false);
      }
    } catch (error) {
      console.error('Failed to save group:', error);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-white max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEditMode ? 'Edit Group' : 'Create Scheduled Group'}</DialogTitle>
          <DialogDescription>
            Configure the schedule and goals for this group
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Group Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Group Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Weekly Status Checks"
              className={errors.name ? 'border-red-500' : ''}
            />
            {errors.name && <p className="text-sm text-red-500">{errors.name}</p>}
          </div>

          {/* Frequency - Days of Week */}
          <div className="space-y-2">
            <Label>Frequency</Label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {DAYS_OF_WEEK.map((day) => (
                <label
                  key={day.value}
                  className="flex items-center gap-2 p-2 rounded-md border cursor-pointer hover:bg-gray-50"
                >
                  <input
                    type="checkbox"
                    checked={frequency.includes(day.value)}
                    onChange={() => toggleDay(day.value)}
                    className="size-4"
                  />
                  <span className="text-sm">{day.label}</span>
                </label>
              ))}
            </div>
            {errors.frequency && (
              <p className="text-sm text-red-500">{errors.frequency}</p>
            )}
          </div>

          {/* Time of Day */}
          <div className="space-y-2">
            <Label htmlFor="time">Time of Day</Label>
            <Input
              id="time"
              type="time"
              value={timeOfDay}
              onChange={(e) => setTimeOfDay(e.target.value)}
              className="w-32"
            />
          </div>

          {/* Goal Type */}
          <div className="space-y-2">
            <Label htmlFor="goalType">Goal</Label>
            <Select value={goalType} onValueChange={(value) => setGoalType(value as GoalType)}>
              <SelectTrigger id="goalType" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {GOAL_TYPE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Goal Description - shown only for user_specified */}
          {goalType === 'user_specified' && (
            <div className="space-y-2">
              <Label htmlFor="goalDescription">Goal Description</Label>
              <Textarea
                id="goalDescription"
                value={goalDescription}
                onChange={(e) => setGoalDescription(e.target.value)}
                placeholder="Describe what you want the AI to accomplish..."
                rows={4}
                className={errors.goalDescription ? 'border-red-500' : ''}
              />
              {errors.goalDescription && (
                <p className="text-sm text-red-500">{errors.goalDescription}</p>
              )}
            </div>
          )}

          {/* Who to Call */}
          <div className="space-y-2">
            <Label htmlFor="whoToCall">Who to Call</Label>
            <Select
              value={whoToCall}
              onValueChange={(value) => setWhoToCall(value as WhoToCall)}
            >
              <SelectTrigger id="whoToCall" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {WHO_TO_CALL_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={createGroup.isPending || updateGroup.isPending}
          >
            {createGroup.isPending || updateGroup.isPending
              ? 'Saving...'
              : isEditMode
                ? 'Update Group'
                : 'Create Group'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

