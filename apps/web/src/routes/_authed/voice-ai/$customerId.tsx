// Import Maive logo
import MaiveLogo from '@maive/brand/logos/Maive-Main-Icon.png';

import { Link, createFileRoute } from '@tanstack/react-router';
import { ArrowLeft } from 'lucide-react';

// import { useCustomer } from '@/clients/customer-crm';
// import { createOutboundCall } from '@/clients/voice-ai';
// import Loading from '@/components/Loading';
// import { Button } from '@/components/ui/button';
// import {
//     Card,
//     CardContent,
//     CardDescription,
//     CardHeader,
//     CardTitle,
// } from '@/components/ui/card';
// import { CustomerDetailsComponent } from '@/components/ui/customer-details';
// import { Input } from '@/components/ui/input';
// import { Label } from '@/components/ui/label';

export const Route = createFileRoute('/_authed/voice-ai/$customerId')({
  component: CustomerVoiceAI,
});

function CustomerVoiceAI() {
  const { customerId } = Route.useParams();

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <Link
          to="/voice-ai"
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Customer Search
        </Link>
      </div>

      <div className="text-center">
        <img src={MaiveLogo} alt="Maive Logo" className="w-16 h-auto mx-auto mb-4" />
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Customer Voice AI - Coming Soon
        </h1>
        <p className="text-lg text-gray-600 mb-2">
          Customer ID: {customerId}
        </p>
        <p className="text-lg text-gray-600">
          This feature is currently under development.
        </p>
      </div>
    </div>
  );
}
