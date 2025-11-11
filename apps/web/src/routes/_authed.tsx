import { Outlet, createFileRoute } from '@tanstack/react-router';
import { useAuth } from '../auth';
import HeaderBar from '@/components/layout/HeaderBar';
import SidebarNav from '@/components/layout/SidebarNav';
import { Spinner } from '@/components/ui/spinner';

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
      <div className="flex h-screen">
        <SidebarNav user={auth.user} />
        <div className="flex flex-col flex-1">
          <HeaderBar user={auth.user} />
          <main className="flex-1 overflow-auto">
            <Outlet />
          </main>
        </div>
      </div>
    );
  },
});
