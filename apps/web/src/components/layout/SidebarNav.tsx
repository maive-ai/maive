import collapsedLogo from '@maive/brand/logos/Maive-Light-Avatar.png';
import fullLogo from '@maive/brand/logos/Maive-Main-Logo.png';
import { Link } from '@tanstack/react-router';
import { ChevronLeft, ChevronRight, Settings } from 'lucide-react';
import { useState } from 'react';
import type { User } from '@maive/api/client';
import { SettingsModal } from './SettingsModal';
import { Button } from '@/components/ui/button';
import { navItems } from '@/config/navRoutes';
import { cn } from '@/lib/utils';

export type SidebarNavProps = {
  user: User | null;
};

export default function SidebarNav({ user }: SidebarNavProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const role = user?.role;

  return (
    <aside
      className={cn(
        'hidden md:block relative bg-neutral-50 transition-all duration-200',
        collapsed ? 'w-16' : 'w-52',
      )}
    >
      <div
        className="flex flex-col items-center"
        style={{ minHeight: '4rem', justifyContent: 'center' }}
      >
        {collapsed ? (
          <img
            src={collapsedLogo}
            alt="Maive Logo Collapsed"
            className="w-12 h-12 rounded-lg"
          />
        ) : (
          <img src={fullLogo} alt="Maive Logo" className="w-32" />
        )}
      </div>
      <div className="h-[calc(100vh-4rem)] overflow-auto py-6 flex flex-col">
        <nav
          className={cn('flex flex-col space-y-1 flex-1', collapsed ? 'px-2' : 'px-4')}
        >
          {navItems
            .filter(
              (item) =>
                !item.requiredRoles ||
                (role && item.requiredRoles.includes(role)),
            )
            .map((item) => {
              const isCreateWorkflow = item.label === 'New Workflow';
              return (
                <Link
                  key={item.route.id}
                  to={item.route.fullPath}
                  className={cn(
                    'flex items-center text-sm font-medium transition-colors rounded-md',
                    collapsed ? 'justify-center p-2' : 'gap-3 px-3 py-2',
                    isCreateWorkflow
                      ? 'bg-primary-900 text-primary-50 shadow-xs hover:bg-primary-800'
                      : 'hover:bg-neutral-700/10',
                  )}
                >
                  {item.icon && (
                    <item.icon
                      className={cn(
                        'h-5 w-5 flex-shrink-0',
                        isCreateWorkflow ? 'text-primary-50' : 'text-gray-500',
                      )}
                    />
                  )}
                  {!collapsed && item.label}
                </Link>
              );
            })}
          <button
            onClick={() => setSettingsOpen(true)}
            className={cn(
              'flex items-center text-sm font-medium transition-colors rounded-md hover:bg-neutral-700/10 cursor-pointer mt-auto',
              collapsed ? 'justify-center p-2' : 'gap-3 px-3 py-2',
            )}
            aria-label="Settings"
          >
            <Settings className="h-5 w-5 flex-shrink-0 text-gray-500" />
            {!collapsed && 'Settings'}
          </button>
        </nav>
      </div>
      <Button
        variant="tertiary"
        size="icon"
        aria-label="Toggle sidebar"
        onClick={() => setCollapsed((c) => !c)}
        className="absolute bottom-4 right-0 translate-x-1/2 z-10 shadow-sm border border-primary-600 flex items-center justify-center transition-all duration-200 hover:scale-105"
      >
        {collapsed ? (
          <ChevronRight className="h-4 w-4 text-primary-600" />
        ) : (
          <ChevronLeft className="h-4 w-4 text-primary-600" />
        )}
      </Button>
      <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />
    </aside>
  );
}
