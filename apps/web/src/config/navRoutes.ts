import type { AnyRoute } from '@tanstack/react-router';
import type { LucideIcon } from 'lucide-react';
import { Mic, SquarePlus, Workflow } from 'lucide-react';
import { env } from '../env';
import { Route as VoiceAIRoute } from '../routes/_authed/voice-ai/index.tsx';
import { Route as WorkflowsRoute } from '../routes/_authed/workflows/index.tsx';
import { Route as BuilderRoute } from '../routes/_authed/workflows/new_workflow.tsx';

export type NavItem = {
  label: string;
  route: AnyRoute;
  requiredRoles?: string[];
  icon?: LucideIcon;
};

const allNavItems: NavItem[] = [
  {
    label: 'New Workflow',
    route: BuilderRoute,
    icon: SquarePlus,
  },
  {
    label: 'Workflows',
    route: WorkflowsRoute,
    icon: Workflow,
  },
  {
    label: 'Claim Check',
    route: VoiceAIRoute,
    icon: Mic,
  },
];

export const navItems: NavItem[] = allNavItems.filter((item) => {
  // Filter out workflow items if workflows are disabled
  if (!env.PUBLIC_ENABLE_WORKFLOWS) {
    return !['New Workflow', 'Workflows'].includes(item.label);
  }
  return true;
});
