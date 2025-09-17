import Loading from '@/components/Loading';
import HeaderBar from '@/components/layout/HeaderBar';
import SidebarNav from '@/components/layout/SidebarNav';
import { Outlet, createFileRoute } from '@tanstack/react-router';
import { useAuth } from '../auth';

export const Route: any = createFileRoute('/_authed')({
  component: () => {
    const auth = useAuth();
    if (auth.isLoading) {
      return <Loading />;
    }
    if (!auth.isAuthenticated) {
      auth.signIn();
      return <Loading />;
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
