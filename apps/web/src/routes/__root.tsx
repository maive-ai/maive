import NotFound from '@/components/NotFound';
import { Outlet, createRootRouteWithContext } from '@tanstack/react-router';
import type { AuthContext } from '../auth';
// import { AssistantUIProvider } from '@/components/assistant-ui/AssistantUIProvider';

interface RouterContext {
  auth: AuthContext;
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: () => (
    // <AssistantUIProvider>
    <Outlet />
    // </AssistantUIProvider>
  ),
  notFoundComponent: NotFound,
});
