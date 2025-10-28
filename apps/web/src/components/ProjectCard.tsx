import { Building2, CheckCircle2, Circle, Mail, MapPin, Phone } from 'lucide-react';

import type { Project } from '@/clients/crm';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { formatPhoneNumber, getStatusColor } from '@/lib/utils';

interface ProjectCardProps {
  project: Project;
  onClick?: (projectId: string) => void;
  isSelectMode?: boolean;
  isSelected?: boolean;
  onSelect?: (projectId: string) => void;
}

export function ProjectCard({
  project,
  onClick,
  isSelectMode = false,
  isSelected = false,
  onSelect
}: ProjectCardProps) {
  // Extract data from provider_data
  const providerData = project.provider_data as any;

  const customerName = project.customer_name || providerData?.customerName || 'Customer Name';
  const address = project.address_line1 || providerData?.address || '123 Main St, City, State 12345';
  const phone = formatPhoneNumber(providerData?.customer_phone || providerData?.phone);
  const email = providerData?.customer_email || providerData?.email || 'Not available';

  const handleClick = (): void => {
    if (isSelectMode && onSelect) {
      onSelect(project.id);
    } else if (onClick) {
      onClick(project.id);
    }
  };

  return (
    <Card
      className={`cursor-pointer transition-all hover:shadow-lg hover:scale-[1.02] relative ${
        isSelected ? 'ring-2 ring-blue-500 border-blue-500' : ''
      }`}
      onClick={handleClick}
    >
      {/* Selection indicator */}
      {isSelectMode && (
        <div className="absolute top-3 right-3 z-10">
          {isSelected ? (
            <CheckCircle2 className="size-6 text-blue-500 fill-white" />
          ) : (
            <Circle className="size-6 text-gray-400" />
          )}
        </div>
      )}

      <CardHeader className="pb-4">
        <div className="flex items-center gap-3">
          <div className="size-10 rounded-lg bg-gradient-to-br from-orange-400 to-pink-400 flex items-center justify-center">
            <Building2 className="size-6 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900">{customerName}</h3>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3 text-sm">
        {/* Address */}
        <div className="flex items-start gap-3">
          <MapPin className="size-4 text-gray-400 mt-0.5 shrink-0" />
          <p className="text-gray-600">{address}</p>
        </div>

        {/* Phone */}
        <div className="flex items-start gap-3">
          <Phone className="size-4 text-gray-400 mt-0.5 shrink-0" />
          <p className="text-gray-600">{phone}</p>
        </div>

        {/* Email */}
        <div className="flex items-start gap-3">
          <Mail className="size-4 text-gray-400 mt-0.5 shrink-0" />
          <p className="text-gray-600 break-all">{email}</p>
        </div>

        {/* Status Badge */}
        <div className="pt-3">
          <div className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getStatusColor(project.status)}`}>
            {project.status}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

