import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { AlertCircle, FileSearch, Search } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useFetchProjects } from '@/clients/crm';
import { ProjectCard } from '@/components/ProjectCard';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

export const Route = createFileRoute('/_authed/projects')({
  component: Projects,
});

function Projects() {
  const { data, isLoading, isError, error } = useFetchProjects();
  const [searchQuery, setSearchQuery] = useState<string>('');
  const navigate = useNavigate();

  const handleProjectClick = (projectId: string): void => {
    navigate({ to: '/project-detail', search: { projectId } });
  };

  // Filter projects based on search query
  const filteredProjects = useMemo(() => {
    if (!data?.projects || !searchQuery.trim()) {
      return data?.projects || [];
    }

    const query = searchQuery.toLowerCase().trim();

    return data.projects.filter((project) => {
      const providerData = project.provider_data as any;

      // Search across multiple fields
      const searchableFields = [
        project.id,
        project.status,
        project.customer_name,
        project.claim_number,
        project.number,
        providerData?.customerName,
        providerData?.address,
        providerData?.phone,
        providerData?.email,
        providerData?.insuranceAgency,
        providerData?.insuranceAgencyContact?.name,
        providerData?.adjusterName,
        providerData?.adjusterContact?.name,
      ];

      return searchableFields.some((field) =>
        field?.toString().toLowerCase().includes(query)
      );
    });
  }, [data?.projects, searchQuery]);

  // Loading State
  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
          <p className="text-gray-600 mt-1">Loading your projects...</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6 space-y-4">
                <div className="h-10 bg-gray-200 rounded" />
                <div className="space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-3/4" />
                  <div className="h-4 bg-gray-200 rounded w-1/2" />
                  <div className="h-4 bg-gray-200 rounded w-2/3" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // Error State
  if (isError) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
        </div>
        <div className="flex flex-col items-center justify-center py-12">
          <div className="rounded-full bg-red-100 p-4 mb-4">
            <AlertCircle className="size-8 text-red-600" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Failed to load projects
          </h2>
          <p className="text-gray-600 text-center max-w-md">
            {error?.message || 'An unexpected error occurred while fetching projects.'}
          </p>
        </div>
      </div>
    );
  }

  // Empty State
  if (!data || data.projects.length === 0) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
          <p className="text-gray-600 mt-1">
            {data ? `${data.total_count} projects` : 'No projects found'}
          </p>
        </div>
        <div className="flex flex-col items-center justify-center py-12">
          <div className="rounded-full bg-gray-100 p-4 mb-4">
            <FileSearch className="size-8 text-gray-400" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            No projects found
          </h2>
          <p className="text-gray-600 text-center max-w-md">
            There are currently no projects in your CRM system.
          </p>
        </div>
      </div>
    );
  }

  // Success State with Projects Grid
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-gray-400" />
          <Input
            type="text"
            placeholder="Search by name, address, phone, or claim number..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 h-12 text-base"
          />
        </div>
        {searchQuery && (
          <p className="text-sm text-gray-600 mt-2">
            {filteredProjects.length} {filteredProjects.length === 1 ? 'result' : 'results'} found
          </p>
        )}
      </div>

      {/* No Results State */}
      {searchQuery && filteredProjects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="rounded-full bg-gray-100 p-4 mb-4">
            <FileSearch className="size-8 text-gray-400" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            No results found
          </h2>
          <p className="text-gray-600 text-center max-w-md">
            No projects match your search query &ldquo;{searchQuery}&rdquo;. Try a different search term.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onClick={handleProjectClick}
            />
          ))}
        </div>
      )}
    </div>
  );
}

