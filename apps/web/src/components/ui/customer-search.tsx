import {
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
  FileText,
  MapPin,
  Phone,
  Search,
  XCircle,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { useCustomers, type CustomerDetails } from '@/clients/customer-crm';
import { Input } from './input';
import { Label } from './label';

interface CustomerSearchProps {
  onCustomerSelect: (customer: CustomerDetails) => void;
}

// Utility functions for claim status display
function getClaimStatusIcon(status?: string) {
  switch (status) {
    case 'approved':
      return <CheckCircle className="w-3 h-3 text-green-600" />;
    case 'denied':
      return <XCircle className="w-3 h-3 text-red-600" />;
    case 'pending_review':
      return <Clock className="w-3 h-3 text-yellow-600" />;
    case 'needs_documents':
      return <AlertTriangle className="w-3 h-3 text-orange-600" />;
    case 'payment_issued':
      return <DollarSign className="w-3 h-3 text-green-600" />;
    default:
      return <Clock className="w-3 h-3 text-gray-400" />;
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

export function CustomerSearch({ onCustomerSelect }: CustomerSearchProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const { data: customers, isLoading } = useCustomers(debouncedQuery);

  const handleCustomerSelect = (customer: CustomerDetails) => {
    onCustomerSelect(customer);
    setSearchQuery(''); // Clear search after selection
  };

  return (
    <div className="space-y-6">
      <div>
        <Label
          htmlFor="customer-search"
          className="text-lg font-semibold text-gray-900"
        >
          Search Customers
        </Label>
        <div className="relative mt-3">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <Input
            id="customer-search"
            type="text"
            placeholder="Search by name, address, phone, or claim number..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-12 h-12 text-base"
          />
        </div>
      </div>

      {isLoading && (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
          <p className="text-sm text-gray-500 mt-2">Searching customers...</p>
        </div>
      )}

      {customers && customers.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">
              Search Results
            </h2>
            <span className="text-sm text-gray-500">
              {customers.length} found
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {customers.map((customer) => (
              <div
                key={customer.id}
                className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors hover:shadow-md"
                onClick={() => handleCustomerSelect(customer)}
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-medium text-gray-900 truncate">
                          {customer.homeownerName}
                        </h4>
                        {customer.claimStatus && (
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium flex-shrink-0 ${getClaimStatusColor(customer.claimStatus)}`}
                          >
                            {getClaimStatusIcon(customer.claimStatus)}
                            {getClaimStatusLabel(customer.claimStatus)}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-400 font-mono mb-2">
                        ID: {customer.id}
                      </p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <p className="text-sm text-gray-600 flex items-start gap-2">
                      <MapPin className="w-3 h-3 mt-0.5 flex-shrink-0" />
                      <span className="line-clamp-2">{customer.address}</span>
                    </p>
                    <p className="text-sm text-gray-600 flex items-center gap-2">
                      <Phone className="w-3 h-3 flex-shrink-0" />
                      <span className="truncate">{customer.phoneNumber}</span>
                    </p>
                    {customer.claimNumber && (
                      <p className="text-sm text-gray-600 flex items-center gap-2">
                        <FileText className="w-3 h-3 flex-shrink-0" />
                        <span className="truncate">
                          Claim: {customer.claimNumber}
                        </span>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {customers && customers.length === 0 && searchQuery && (
        <div className="text-center py-8 text-gray-500">
          <Search className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No customers found matching &ldquo;{searchQuery}&rdquo;</p>
          <p className="text-sm">
            Try searching by name, address, phone, or claim number
          </p>
        </div>
      )}
    </div>
  );
}
