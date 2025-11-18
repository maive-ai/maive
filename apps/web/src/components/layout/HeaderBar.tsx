import { useAuth } from '@/auth';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { User } from '@maive/api/client';
import { LogOut, Settings } from 'lucide-react';
import { useState } from 'react';
import { SettingsModal } from './SettingsModal';

export type HeaderBarProps = {
  user: User | null;
};

export default function HeaderBar({ user }: HeaderBarProps) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const { signOut } = useAuth();

  const handleSignOut = async () => {
    await signOut();
  };

  // Get user initials for avatar
  const getInitials = () => {
    if (user?.name) {
      return user.name
        .split(' ')
        .map(n => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
    }
    if (user?.email) {
      return user.email.slice(0, 2).toUpperCase();
    }
    return 'U';
  };

  // Extract organization name from email domain or use org name from backend
  const getOrgName = () => {
    if (user?.email) {
      const domain = user.email.split('@')[1];
      if (domain) {
        const orgName = domain.split('.')[0];
        if (orgName) {
          return orgName.charAt(0).toUpperCase() + orgName.slice(1);
        }
      }
    }
    return 'Organization';
  };

  return (
    <>
      <header className="flex h-16 shrink-0 items-center justify-end gap-2 bg-neutral-50 px-6 transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12">
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-3 rounded-full transition-colors hover:bg-neutral-100 p-1">
                <Avatar className="h-9 w-9 border-2 border-primary-900">
                  <AvatarFallback className="bg-primary-900 text-white text-sm font-medium">
                    {getInitials()}
                  </AvatarFallback>
                </Avatar>
              </button>
            </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-72">
            <DropdownMenuLabel>
              <div className="flex items-center gap-3">
                <Avatar className="h-12 w-12 border-2 border-primary-900">
                  <AvatarFallback className="bg-primary-900 text-white text-lg font-medium">
                    {getInitials()}
                  </AvatarFallback>
                </Avatar>
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{user?.email}</p>
                  <p className="text-xs text-muted-foreground">{getOrgName()}</p>
                </div>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => setIsSettingsOpen(true)}>
              <Settings className="mr-2 h-4 w-4" />
              <span>Settings</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleSignOut}>
              <LogOut className="mr-2 h-4 w-4" />
              <span>Sign out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </header>

      <SettingsModal open={isSettingsOpen} onOpenChange={setIsSettingsOpen} />
    </>
  );
}
