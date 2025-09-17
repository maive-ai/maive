// Import CRM logos
import AccuLynxLogo from '@maive/brand/logos/integrations/acculynx/acculynx_logo.png';
import JobNimbusLogo from '@maive/brand/logos/integrations/jobnimbus/jobnimbus_logo.png';
import MondayLogo from '@maive/brand/logos/integrations/monday/monday_logo.png';
import ServiceTitanLogo from '@maive/brand/logos/integrations/servicetitan/ServiceTitan_Logo_Black_2.png';

import { createFileRoute, useNavigate } from '@tanstack/react-router';

import {
  getConfiguredCrmLabel,
  getConfiguredCrmSystem,
  type CustomerDetails,
} from '@/clients/customer-crm';
import { CustomerSearch } from '@/components/ui/customer-search';

export const Route = createFileRoute('/_authed/voice-ai/')({
  component: VoiceAI,
});

function getCrmLogo(source: CustomerDetails['crmSource']): string {
  switch (source) {
    case 'servicetitan':
      return ServiceTitanLogo;
    case 'jobnimbus':
      return JobNimbusLogo;
    case 'acculynx':
      return AccuLynxLogo;
    case 'monday':
      return MondayLogo;
    default:
      return ServiceTitanLogo; // fallback
  }
}

function VoiceAI() {
  const navigate = useNavigate();

  const handleCustomerSelect = (customer: CustomerDetails) => {
    console.log('Navigating to customer:', customer.id);
    navigate({
      to: '/voice-ai/$customerId',
      params: { customerId: customer.id },
    });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header Section */}
      <div className="mb-8">
        <div className="flex items-center gap-4 mb-2">
          <img
            src={getCrmLogo(getConfiguredCrmSystem())}
            alt={`${getConfiguredCrmLabel()} logo`}
            className="h-16 w-auto"
          />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {getConfiguredCrmLabel()}
            </h1>
            <p className="text-lg text-gray-600">Customer Lookup</p>
          </div>
        </div>
      </div>

      {/* Search Section */}
      <CustomerSearch onCustomerSelect={handleCustomerSelect} />
    </div>
  );
}
