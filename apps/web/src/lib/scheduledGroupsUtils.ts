/**
 * Shared utilities and formatters for scheduled groups.
 */

import type { GoalType, WhoToCall } from '@/clients/scheduledGroups';

export const DAY_MAP: Record<string, string> = {
  monday: 'Mon',
  tuesday: 'Tue',
  wednesday: 'Wed',
  thursday: 'Thu',
  friday: 'Fri',
  saturday: 'Sat',
  sunday: 'Sun',
};

export const GOAL_TYPE_MAP: Record<string, string> = {
  status_check: 'Status Check',
  locate_check: 'Locate Check',
  user_specified: 'User Specified',
  ai_determined: 'AI Determined',
};

export const WHO_TO_CALL_MAP: Record<string, string> = {
  adjuster: 'Adjuster',
  insurance_carrier: 'Insurance Carrier',
  ai_determines: 'AI Determines',
};

// Days of week for use in forms
export const DAYS_OF_WEEK = [
  { value: 'monday', label: 'Monday' },
  { value: 'tuesday', label: 'Tuesday' },
  { value: 'wednesday', label: 'Wednesday' },
  { value: 'thursday', label: 'Thursday' },
  { value: 'friday', label: 'Friday' },
  { value: 'saturday', label: 'Saturday' },
  { value: 'sunday', label: 'Sunday' },
] as const;

// Goal type options for use in forms
export const GOAL_TYPE_OPTIONS: { value: GoalType; label: string }[] = [
  { value: 'status_check', label: 'Status Update' },
  { value: 'locate_check', label: 'Locate Check' },
  { value: 'ai_determined', label: 'AI Determined' },
  { value: 'user_specified', label: 'User Specified' },
];

// Who to call options for use in forms
export const WHO_TO_CALL_OPTIONS: { value: WhoToCall; label: string }[] = [
  { value: 'adjuster', label: 'Adjuster' },
  { value: 'insurance_carrier', label: 'Insurance Carrier' },
  { value: 'ai_determines', label: 'AI Determines' },
];

/**
 * Convert time from HH:MM:SS format to HH:MM format for input fields.
 * @param timeWithSeconds - Time string in HH:MM:SS format
 * @returns Time string in HH:MM format
 */
export function timeToInputFormat(timeWithSeconds: string): string {
  return timeWithSeconds.substring(0, 5);
}

/**
 * Convert time from HH:MM format to HH:MM:SS format for API.
 * @param timeWithoutSeconds - Time string in HH:MM format
 * @returns Time string in HH:MM:SS format
 */
export function timeToApiFormat(timeWithoutSeconds: string): string {
  return `${timeWithoutSeconds}:00`;
}

/**
 * Format an array of day strings into abbreviated day names.
 * @param frequency - Array of day strings (e.g., ['monday', 'wednesday'])
 * @returns Formatted string (e.g., 'Mon, Wed')
 */
export function formatFrequency(frequency: string[]): string {
  return frequency.map((day) => DAY_MAP[day.toLowerCase()] || day).join(', ');
}

/**
 * Format a goal type enum value into a human-readable string.
 * @param goalType - Goal type enum value
 * @returns Formatted string (e.g., 'Status Check')
 */
export function formatGoalType(goalType: string): string {
  return GOAL_TYPE_MAP[goalType] || goalType;
}

/**
 * Format a who to call enum value into a human-readable string.
 * @param whoToCall - Who to call enum value
 * @returns Formatted string (e.g., 'Adjuster')
 */
export function formatWhoToCall(whoToCall: string): string {
  return WHO_TO_CALL_MAP[whoToCall] || whoToCall;
}

