import type { ProjectStatusResponse } from '@/clients/crm';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { getStatusColor } from '@/lib/utils';
import { Building2, Mail, MapPin, Phone } from 'lucide-react';

interface ProjectCardProps {
  project: ProjectStatusResponse;
  onClick?: (projectId: string) => void;
}

export function ProjectCard({ project, onClick }: ProjectCardProps) {
  // Extract data from provider_data (camelCase format from mock CRM)
  const providerData = project.provider_data as any;
  
  const customerName = providerData?.customerName || 'Customer Name';
  const address = providerData?.address || '123 Main St, City, State 12345';
  const phone = providerData?.phone || '+1-555-0000';
  const email = providerData?.email || 'customer@example.com';

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

