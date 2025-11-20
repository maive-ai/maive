// Import CRM logos
import AccuLynxLogo from '@maive/brand/logos/integrations/acculynx/acculynx_logo.png';
import JobNimbusLogo from '@maive/brand/logos/integrations/jobnimbus/jobnimbus_logo.png';
import MondayLogo from '@maive/brand/logos/integrations/monday/monday_logo.png';
import ServiceTitanLogo from '@maive/brand/logos/integrations/servicetitan/ServiceTitan_Logo_Black_2.png';

import {
  AlertTriangle,
  Building2,
  Calendar,
  CheckCircle,
  Clock,
  DollarSign,
  FileText,
  Mail,
  MapPin,
  Phone,
  User,
  XCircle,
} from 'lucide-react';
import { Button } from './button';
import { Label } from './label';

// import { type CustomerDetails } from '@/clients/customer-crm';

// Placeholder type for CustomerDetails
interface CustomerDetails {
  id: string;
  homeownerName: string;
  address: string;
  phoneNumber: string;
  email?: string;
  claimNumber?: string;
  dateOfLoss?: string;
  insuranceAgency?: string;
  insuranceAgencyContact?: {
    name: string;
    phone: string;
    email: string;
  };
  adjusterName?: string;
  adjusterContact?: {
    phone: string;
    email: string;
  };
  claimStatus?: string;
  notes?: string;
  nextSteps?: string;
  documentsNeeded?: string[];
  submissionMethod?: string;
  crmSource: 'servicetitan' | 'jobnimbus' | 'acculynx' | 'monday';
}

interface CustomerDetailsProps {
  customer: CustomerDetails;
  onClearSelection?: () => void;
  showClearButton?: boolean;
}

// Utility function to get CRM logo
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

// Utility functions for claim status display
function getClaimStatusIcon(status?: string) {
  switch (status) {
    case 'approved':
      return <CheckCircle className="w-4 h-4 text-green-600" />;
    case 'denied':
      return <XCircle className="w-4 h-4 text-red-600" />;
    case 'pending_review':
      return <Clock className="w-4 h-4 text-yellow-600" />;
    case 'needs_documents':
      return <AlertTriangle className="w-4 h-4 text-orange-600" />;
    case 'payment_issued':
      return <DollarSign className="w-4 h-4 text-green-600" />;
    default:
      return <Clock className="w-4 h-4 text-gray-400" />;
  }
}

function getClaimStatusLabel(status?: string): string {
  switch (status) {
    case 'approved':
      return 'Approved';
    case 'denied':
      return 'Denied';
    case 'pending_review':
      return 'Pending Review';
    case 'needs_documents':
      return 'Needs Documents';
    case 'payment_issued':
      return 'Payment Issued';
    case 'unknown':
      return 'Unknown';
    default:
      return 'No Status';
  }
}

function getClaimStatusColor(status?: string): string {
  switch (status) {
    case 'approved':
      return 'bg-green-100 text-green-800 border-green-200';
    case 'denied':
      return 'bg-red-100 text-red-800 border-red-200';
    case 'pending_review':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case 'needs_documents':
      return 'bg-orange-100 text-orange-800 border-orange-200';
    case 'payment_issued':
      return 'bg-green-100 text-green-800 border-green-200';
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200';
  }
}

export function CustomerDetailsComponent({
  customer,
  onClearSelection,
  showClearButton = false,
}: CustomerDetailsProps) {
  return (
    <div className="space-y-4">
      {showClearButton && onClearSelection && (
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Customer Details</h3>
          <Button variant="outline" size="sm" onClick={onClearSelection}>
            Change Customer
          </Button>
        </div>
      )}

      <div className="bg-white border rounded-lg p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              src={getCrmLogo(customer.crmSource)}
              alt={`${customer.crmSource} logo`}
              className="h-12 w-auto"
            />
            <div>
              <h4 className="text-xl font-bold text-gray-900">
                {customer.homeownerName}
              </h4>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {customer.claimStatus && (
              <span
                className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getClaimStatusColor(customer.claimStatus)}`}
              >
                {getClaimStatusIcon(customer.claimStatus)}
                {getClaimStatusLabel(customer.claimStatus)}
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div className="flex items-start gap-2">
              <MapPin className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
              <div>
                <Label className="text-sm font-medium text-gray-700">
                  Address
                </Label>
                <p className="text-sm text-gray-900">{customer.address}</p>
              </div>
            </div>

            <div className="flex items-start gap-2">
              <Phone className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
              <div>
                <Label className="text-sm font-medium text-gray-700">
                  Phone
                </Label>
                <p className="text-sm text-gray-900">{customer.phoneNumber}</p>
              </div>
            </div>

            {customer.email && (
              <div className="flex items-start gap-2">
                <Mail className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                <div>
                  <Label className="text-sm font-medium text-gray-700">
                    Email
                  </Label>
                  <p className="text-sm text-gray-900">{customer.email}</p>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-3">
            {customer.claimNumber && (
              <div className="flex items-start gap-2">
                <FileText className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                <div>
                  <Label className="text-sm font-medium text-gray-700">
                    Claim Number
                  </Label>
                  <p className="text-sm text-gray-900">
                    {customer.claimNumber}
                  </p>
                </div>
              </div>
            )}

            {customer.dateOfLoss && (
              <div className="flex items-start gap-2">
                <Calendar className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                <div>
                  <Label className="text-sm font-medium text-gray-700">
                    Date of Loss
                  </Label>
                  <p className="text-sm text-gray-900">{customer.dateOfLoss}</p>
                </div>
              </div>
            )}

            {customer.insuranceAgency && (
              <div className="flex items-start gap-2">
                <Building2 className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                <div>
                  <Label className="text-sm font-medium text-gray-700">
                    Insurance Agency
                  </Label>
                  <p className="text-sm text-gray-900">
                    {customer.insuranceAgency}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Insurance Agency Contact */}
        {customer.insuranceAgencyContact && (
          <div className="border-t pt-4">
            <Label className="text-sm font-medium text-gray-700 mb-2 block">
              Insurance Agency Contact
            </Label>
            <div className="bg-gray-50 rounded p-3 space-y-2">
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium">
                  {customer.insuranceAgencyContact.name}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4 text-gray-500" />
                <span className="text-sm">
                  {customer.insuranceAgencyContact.phone}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-gray-500" />
                <span className="text-sm">
                  {customer.insuranceAgencyContact.email}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Adjuster Contact */}
        {customer.adjusterName && customer.adjusterContact && (
          <div className="border-t pt-4">
            <Label className="text-sm font-medium text-gray-700 mb-2 block">
              Adjuster Contact
            </Label>
            <div className="bg-gray-50 rounded p-3 space-y-2">
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium">
                  {customer.adjusterName}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4 text-gray-500" />
                <span className="text-sm">
                  {customer.adjusterContact.phone}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-gray-500" />
                <span className="text-sm">
                  {customer.adjusterContact.email}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Required Actions / Next Steps */}
        {customer.nextSteps && (
          <div className="border-t pt-4">
            <Label className="text-sm font-medium text-gray-700 mb-2 block">
              Next Steps
            </Label>
            <div className="bg-blue-50 border border-blue-200 rounded p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-blue-800">{customer.nextSteps}</p>
              </div>
            </div>
          </div>
        )}

        {/* Documents Needed */}
        {customer.documentsNeeded && customer.documentsNeeded.length > 0 && (
          <div className="border-t pt-4">
            <Label className="text-sm font-medium text-gray-700 mb-2 block">
              Documents Required
            </Label>
            <div className="bg-orange-50 border border-orange-200 rounded p-3">
              <ul className="space-y-1">
                {customer.documentsNeeded.map((doc, index) => (
                  <li
                    key={index}
                    className="flex items-center gap-2 text-sm text-orange-800"
                  >
                    <FileText className="w-3 h-3 text-orange-600" />
                    {doc}
                  </li>
                ))}
              </ul>
              {customer.submissionMethod && (
                <div className="mt-2 pt-2 border-t border-orange-200">
                  <p className="text-xs text-orange-700">
                    Submit via:{' '}
                    <span className="font-medium">
                      {customer.submissionMethod}
                    </span>
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
