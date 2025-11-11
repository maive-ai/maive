import type { AnyRoute } from '@tanstack/react-router';
import type { LucideIcon } from 'lucide-react';
import {
  FilePlus,
  FolderKanban,
  MessageSquare,
  Phone,
  SquarePlus,
  Workflow,
} from 'lucide-react';
import { env } from '../env';
import { Route as ChatRoute } from '../routes/_authed/chat.tsx';
import { Route as CreateProjectRoute } from '../routes/_authed/create-project.tsx';
import { Route as ProjectsRoute } from '../routes/_authed/projects.tsx';
import { Route as SimplePhoneInputRoute } from '../routes/_authed/simple-phone-input.tsx';
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
    label: 'Chat',
    route: ChatRoute,
    icon: MessageSquare,
  },
  {
    label: 'Projects',
    route: ProjectsRoute,
    icon: FolderKanban,
  },
  {
    label: 'Create Project',
    route: CreateProjectRoute,
    icon: FilePlus,
  },
  {
    label: 'Phone Input',
    route: SimplePhoneInputRoute,
    icon: Phone,
  },
];

export const navItems: NavItem[] = allNavItems.filter((item) => {
  // Filter out workflow items if workflows are disabled
  if (!env.PUBLIC_ENABLE_WORKFLOWS) {
    if (['New Workflow', 'Workflows'].includes(item.label)) {
      return false;
    }
  }

  // Filter out create project if demo project creation is disabled
  if (!env.PUBLIC_ENABLE_DEMO_PROJECT_CREATION) {
    if (item.label === 'Create Project') {
      return false;
    }
  }

  // Filter out voice AI items if voice AI is disabled
  if (!env.PUBLIC_ENABLE_VOICE_AI) {
    if (['Projects', 'Phone Input'].includes(item.label)) {
      return false;
    }
  }

  return true;
});
