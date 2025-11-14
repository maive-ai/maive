import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  RouterProvider,
  createRouter,
  type AnyRouter,
} from '@tanstack/react-router';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { PostHogProvider } from 'posthog-js/react';

import { AuthProvider, useAuth } from './auth';
import { Spinner } from './components/ui/spinner';
import { routeTree } from './routeTree.gen';
import { POSTHOG_API_KEY, POSTHOG_API_HOST } from './env';
import './style.css';

// Create a client
const queryClient = new QueryClient();

// Set up a Router instance
const router: AnyRouter = createRouter({
  routeTree,
  defaultPreload: 'intent',
  scrollRestoration: true,
  context: {
    auth: undefined!, // This will be set after we wrap the app in an AuthProvider
  },
});

// Register things for typesafety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}

function InnerApp() {
  const auth = useAuth();
  if (auth.isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center">
        <Spinner className="size-12" />
      </div>
    );
  }
  return <RouterProvider router={router} context={{ auth }} />;
}

function App() {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        <InnerApp />
      </QueryClientProvider>
    </AuthProvider>
  );
}

const rootElement = document.getElementById('app')!;

if (!rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(
    <React.StrictMode>
      <PostHogProvider
        apiKey={POSTHOG_API_KEY}
        options={{
          api_host: POSTHOG_API_HOST,
          defaults: '2025-05-24',
          capture_exceptions: true, // This enables capturing exceptions using Error Tracking
          debug: import.meta.env.MODE === 'development',
        }}
      >
        <App />
      </PostHogProvider>
    </React.StrictMode>,
  );
}