import MaiveLogo from '@maive/brand/logos/Maive-Main-Logo.svg';
import type { AnyRoute } from '@tanstack/react-router';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { Button } from '../../components/ui/button';

export const Route: AnyRoute = createFileRoute('/auth/signup-success')({
  component: SignupSuccessComponent,
});

function SignupSuccessComponent() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen flex items-center justify-center bg-primary-50 p-4">
      <div className="max-w-2xl mx-auto text-center">
        {/* Logo */}
        <div className="mb-8 flex justify-center">
          <img src={MaiveLogo} alt="Maive Logo" className="h-16 w-auto" />
        </div>

        {/* Success Icon */}
        <div className="mb-6">
          <svg
            className="mx-auto h-16 w-16 text-accent-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>

        {/* Main Heading */}
        <h1 className="text-3xl font-bold mb-4 text-primary-900 font-sans">
          Congratulations!
        </h1>

        {/* Content Card */}
        <div className="bg-primary-50 p-8 rounded-lg shadow-lg border border-primary-200">
          <p className="text-lg text-primary-900 leading-relaxed mb-4">
            You've signed up for{' '}
            <span className="font-semibold text-primary-900">Maive</span>, the
            future of AI in industry.
          </p>
          <p className="text-lg text-primary-900 leading-relaxed">
            You'll hear from us shortly to get full access. Get ready to be an
            AI innovator in your organization!
          </p>
        </div>

        {/* Footer */}
        <div className="mt-6">
          <p className="text-sm text-primary-700">
            Thank you for joining us on this exciting journey.
          </p>
        </div>
        <div className="mt-8 flex justify-center">
          <Button onClick={() => navigate({ to: '/workflows' })}>
            Let's go!
          </Button>
        </div>
      </div>
    </div>
  );
}
