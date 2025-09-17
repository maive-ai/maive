import {
  Link,
  createFileRoute,
  redirect,
  type AnyRoute,
} from '@tanstack/react-router';

export const Route: AnyRoute = createFileRoute('/auth/error')({
  beforeLoad: ({ context }) => {
    // If user is already authenticated, redirect to home
    if (context.auth.isAuthenticated) {
      throw redirect({
        to: '/',
      });
    }
  },
  component: AuthErrorComponent,
});

function AuthErrorComponent() {
  // Get error message from URL search params
  const searchParams = new URLSearchParams(window.location.search);
  const errorMessage =
    searchParams.get('message') ||
    'An unknown error occurred during authentication.';

  return (
    <div className="p-4 max-w-md mx-auto mt-8 text-center">
      <div className="mb-4">
        <svg
          className="mx-auto h-12 w-12 text-red-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
          />
        </svg>
      </div>
      <h1 className="text-2xl font-bold mb-2 text-red-600">
        Authentication Failed
      </h1>
      <p className="text-gray-600 mb-6">{errorMessage}</p>
      <div className="space-y-3">
        <Link
          to="/"
          className="inline-block w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded"
        >
          Try Again
        </Link>
        <Link
          to="/"
          className="inline-block w-full bg-gray-500 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded"
        >
          Go Home
        </Link>
      </div>
    </div>
  );
}
