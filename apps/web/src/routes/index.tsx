import MaiveLogo from '@maive/brand/logos/Maive-Main-Logo.svg';
import {
  createFileRoute,
  redirect,
  type AnyRoute,
} from '@tanstack/react-router';
import { useAuth } from '../auth';
import { env } from '../env';
import { Button } from '@/components/ui/button';

export const Route: AnyRoute = createFileRoute('/')({
  beforeLoad: ({ context }) => {
    if (context.auth.isAuthenticated) {
      // Redirect to voice-ai if workflows are disabled, otherwise workflows
      const defaultRoute = env.PUBLIC_ENABLE_WORKFLOWS
        ? '/workflows'
        : '/voice-ai';
      throw redirect({
        to: defaultRoute,
        replace: true, // optional, avoids pushing the "/" into history
      });
    }
  },
  component: HomeComponent,
});

function HomeComponent() {
  const auth = useAuth();

  const handleSignIn = () => {
    auth.signIn();
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-primary-50 px-4">
      <div className="max-w-md w-full text-center space-y-8">
        {/* Logo */}
        <div className="flex justify-center">
          <img src={MaiveLogo} alt="Maive Logo" className="h-20 w-auto" />
        </div>

        {/* Welcome Text */}
        <h1 className="text-3xl font-bold text-primary-900">
          Welcome to Maive!
        </h1>

        {/* Sign In Button */}
        <div className="pt-4">
          <Button onClick={handleSignIn} size="lg">
            Sign In
          </Button>
        </div>
      </div>
    </div>
  );
}
