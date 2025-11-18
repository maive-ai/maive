import fullLogo from '@maive/brand/logos/Maive-Main-Logo.png';
import { Link, useRouterState } from '@tanstack/react-router';
import { Settings, PanelLeft, PanelRight } from 'lucide-react';
import { useState } from 'react';
import type { User } from '@maive/api/client';
import { SettingsModal } from './SettingsModal';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from '@/components/ui/sidebar';
import { Button } from '@/components/ui/button';
import { navItems } from '@/config/navRoutes';
import { env } from '@/env';
import { cn } from '@/lib/utils';

export type AppSidebarProps = {
  user: User | null;
};

export default function AppSidebar({ user, ...props }: AppSidebarProps & React.ComponentProps<typeof Sidebar>) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const role = user?.role;
  const { state, toggleSidebar } = useSidebar();
  const router = useRouterState();
  const currentPath = router.location.pathname;

  return (
    <>
      <Sidebar collapsible="icon" {...props}>
        <SidebarHeader>
          {state === 'collapsed' ? (
            <div className="flex items-center justify-center px-2 py-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="h-8 w-8"
              >
                <PanelRight className="h-5 w-5" />
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-2">
              <SidebarMenu className="flex-1">
                <SidebarMenuItem>
                  <SidebarMenuButton size="lg" asChild className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground">
                    <Link to="/">
                      <div className="grid flex-1 text-left text-sm leading-tight">
                        <img src={fullLogo} alt="Maive Logo" className="w-32" />
                      </div>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="h-8 w-8"
              >
                <PanelLeft className="h-5 w-5" />
              </Button>
            </div>
          )}
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                {navItems
                  .filter(
                    (item) =>
                      !item.requiredRoles ||
                      (role && item.requiredRoles.includes(role)),
                  )
                  .map((item) => {
                    const isCreateWorkflow = item.label === 'New Workflow';
                    const isActive = currentPath === item.route.fullPath;
                    return (
                      <SidebarMenuItem key={item.route.id}>
                        <SidebarMenuButton
                          asChild
                          tooltip={item.label}
                          isActive={isActive}
                          className={cn(
                            'text-base', // 20% bigger text (from 0.875rem to 1rem)
                            isCreateWorkflow &&
                              'bg-primary-900 text-primary-50 shadow-xs hover:bg-primary-800 data-[active=true]:bg-primary-800',
                          )}
                        >
                          <Link to={item.route.fullPath}>
                            {item.icon && (
                              <item.icon
                                className={cn(
                                  'h-6 w-6', // 20% bigger icons (from h-5 w-5 to h-6 w-6)
                                  isCreateWorkflow ? 'text-primary-50' : 'text-gray-500',
                                )}
                              />
                            )}
                            <span>{item.label}</span>
                          </Link>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    );
                  })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
        {env.PUBLIC_ENABLE_VOICE_AI && (
          <SidebarFooter>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  onClick={() => setSettingsOpen(true)}
                  tooltip="Settings"
                  className="text-base"
                >
                  <Settings className="h-6 w-6 text-gray-500" />
                  <span>Settings</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarFooter>
        )}
      </Sidebar>
      <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
