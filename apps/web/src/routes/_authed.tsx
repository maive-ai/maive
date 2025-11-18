import { Outlet, createFileRoute } from '@tanstack/react-router';
import { useAuth } from '../auth';
import HeaderBar from '@/components/layout/HeaderBar';
import AppSidebar from '@/components/layout/AppSidebar';
import { Spinner } from '@/components/ui/spinner';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';

export const Route: any = createFileRoute('/_authed')({
  component: () => {
    const auth = useAuth();
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
  },
});
