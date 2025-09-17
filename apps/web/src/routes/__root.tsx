import { Outlet, createRootRouteWithContext } from '@tanstack/react-router';
import type { AuthContext } from '../auth';
import NotFound from '@/components/NotFound';
import { AssistantUIProvider } from '@/components/assistant-ui/AssistantUIProvider';

interface RouterContext {
  auth: AuthContext;
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: () => (
    <AssistantUIProvider>
      <Outlet />
    </AssistantUIProvider>
  ),
  notFoundComponent: NotFound,
});
