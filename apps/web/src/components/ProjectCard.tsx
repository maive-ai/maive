import { Building2, FileText, Mail, MapPin, Phone, User } from 'lucide-react';
import type { ProjectStatusResponse } from '@/clients/crm';
import { Card, CardContent, CardHeader } from '@/components/ui/card';

interface ProjectCardProps {
  project: ProjectStatusResponse;
  onClick?: (projectId: string) => void;
}

export function ProjectCard({ project, onClick }: ProjectCardProps) {
  // Extract data from provider_data if available
  const providerData = project.provider_data as any;
  
  // Mock/placeholder data structure - will use actual data when available
  const customerName = providerData?.customer_name || 'Customer Name';
  const address = providerData?.address || '123 Main St, City, State 12345';
  const phone = providerData?.phone || '+1-555-0000';
  const email = providerData?.email || 'customer@example.com';
  const claimNumber = providerData?.claim_number || 'CLM' + project.project_id.slice(0, 7);
  const insuranceAgency = providerData?.insurance_agency || 'Insurance Agency';
  const agencyContactName = providerData?.agency_contact_name || 'Contact Name';
  const agencyContactPhone = providerData?.agency_contact_phone || '+1-555-0001';
  const agencyContactEmail = providerData?.agency_contact_email || 'contact@agency.com';
  const adjusterName = providerData?.adjuster_name || 'Adjuster Name';
  const adjusterPhone = providerData?.adjuster_phone || '+1-555-0002';
  const adjusterEmail = providerData?.adjuster_email || 'adjuster@agency.com';

  const handleClick = (): void => {
    if (onClick) {
      onClick(project.project_id);
    }
  };

  return (
    <Card 
      className="cursor-pointer transition-all hover:shadow-lg hover:scale-[1.02]"
      onClick={handleClick}
    >
      <CardHeader className="pb-4">
        <div className="flex items-center gap-3">
          <div className="size-10 rounded-lg bg-gradient-to-br from-orange-400 to-pink-400 flex items-center justify-center">
            <Building2 className="size-6 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900">{customerName}</h3>
            <p className="text-xs text-gray-500 uppercase tracking-wide">
              {project.provider}
            </p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 text-sm">
        {/* Address */}
        <div className="flex items-start gap-3">
          <MapPin className="size-5 text-gray-400 mt-0.5 shrink-0" />
          <div>
            <p className="font-medium text-gray-700">Address</p>
            <p className="text-gray-600">{address}</p>
          </div>
        </div>

        {/* Phone */}
        <div className="flex items-start gap-3">
          <Phone className="size-5 text-gray-400 mt-0.5 shrink-0" />
          <div>
            <p className="font-medium text-gray-700">Phone</p>
            <p className="text-gray-600">{phone}</p>
          </div>
        </div>

        {/* Email */}
        <div className="flex items-start gap-3">
          <Mail className="size-5 text-gray-400 mt-0.5 shrink-0" />
          <div>
            <p className="font-medium text-gray-700">Email</p>
            <p className="text-gray-600 break-all">{email}</p>
          </div>
        </div>

        <div className="border-t pt-4 space-y-3">
          {/* Claim Number & Insurance */}
          <div className="flex items-start gap-3">
            <FileText className="size-5 text-gray-400 mt-0.5 shrink-0" />
            <div className="flex-1 grid grid-cols-2 gap-4">
              <div>
                <p className="font-medium text-gray-700">Claim Number</p>
                <p className="text-gray-600">{claimNumber}</p>
              </div>
              <div>
                <p className="font-medium text-gray-700">Insurance Agency</p>
                <p className="text-gray-600">{insuranceAgency}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Insurance Agency Contact */}
        <div className="border-t pt-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Insurance Agency Contact
          </p>
          <div className="space-y-2 pl-2">
            <div className="flex items-center gap-2">
              <User className="size-4 text-gray-400" />
              <p className="text-gray-700">{agencyContactName}</p>
            </div>
            <div className="flex items-center gap-2">
              <Phone className="size-4 text-gray-400" />
              <p className="text-gray-600">{agencyContactPhone}</p>
            </div>
            <div className="flex items-center gap-2">
              <Mail className="size-4 text-gray-400" />
              <p className="text-gray-600 break-all">{agencyContactEmail}</p>
            </div>
          </div>
        </div>

        {/* Adjuster Contact */}
        <div className="border-t pt-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Adjuster Contact
          </p>
          <div className="space-y-2 pl-2">
            <div className="flex items-center gap-2">
              <User className="size-4 text-gray-400" />
              <p className="text-gray-700">{adjusterName}</p>
            </div>
            <div className="flex items-center gap-2">
              <Phone className="size-4 text-gray-400" />
              <p className="text-gray-600">{adjusterPhone}</p>
            </div>
            <div className="flex items-center gap-2">
              <Mail className="size-4 text-gray-400" />
              <p className="text-gray-600 break-all">{adjusterEmail}</p>
            </div>
          </div>
        </div>

        {/* Status Badge */}
        <div className="border-t pt-4">
          <div className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            Status: {project.status}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

