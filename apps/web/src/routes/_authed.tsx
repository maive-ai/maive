import { Outlet, createFileRoute } from '@tanstack/react-router';

import AppSidebar from '@/components/layout/AppSidebar';
import HeaderBar from '@/components/layout/HeaderBar';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
import { Spinner } from '@/components/ui/spinner';
import { useTwilioDevice } from '@/hooks/useTwilioDevice';
import { useAuth } from '../auth';

function AuthedLayout() {
  const auth = useAuth();

  // Initialize Twilio Device (conditionally based on backend provider)
  useTwilioDevice();

  if (auth.isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center">
        <Spinner className="size-12" />
      </div>
    );
  }

  if (!auth.isAuthenticated) {
    auth.signIn();
    return (
      <div className="flex h-screen w-screen items-center justify-center">
        <Spinner className="size-12" />
      </div>
    );
  }

  return (
    <SidebarProvider>
      <AppSidebar user={auth.user} />
      <SidebarInset>
        <HeaderBar user={auth.user} />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}

export const Route: any = createFileRoute('/_authed')({
  component: AuthedLayout,
});
