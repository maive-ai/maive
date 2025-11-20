import { createFileRoute, useNavigate } from '@tanstack/react-router';
import {
  AlertCircle,
  Building2,
  FileText,
  Loader2,
  Plus,
  Search,
  Trash2,
  User,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import {
  useCreateMockProject,
  useFetchProjects,
  useUpdateMockProject,
  type MockNote,
  type MockProject,
  type Project,
} from '@/clients/crm';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { env } from '@/env';
import { useProjectSearch } from '@/hooks/useProjectSearch';

export const Route = createFileRoute('/_authed/create-project')({
  component: CreateProject,
});

const DEFAULT_PHONE = '+17032681917';
const DEFAULT_ADDRESS = '123 Main St, Austin, TX 78701';

const STATUS_OPTIONS = [
  { value: 'Scheduled', label: 'Scheduled' },
  { value: 'Dispatched', label: 'Dispatched' },
  { value: 'In Progress', label: 'In Progress' },
  { value: 'Hold', label: 'Hold' },
  { value: 'Completed', label: 'Completed' },
  { value: 'Canceled', label: 'Canceled' },
] as const;

function CreateProject() {
  const navigate = useNavigate();
  const createProjectMutation = useCreateMockProject();
  const updateProjectMutation = useUpdateMockProject();
  const { data: projectsData } = useFetchProjects(1, 100);

  // Mode toggle state
  const [isEditMode, setIsEditMode] = useState(false);

  // Edit mode state
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Filter projects based on search query
  const filteredProjects = useProjectSearch(
    projectsData?.projects,
    searchQuery,
  );

  // Form state
  const [customerName, setCustomerName] = useState('');
  const [address, setAddress] = useState(DEFAULT_ADDRESS);
  const [phone, setPhone] = useState(DEFAULT_PHONE);
  const [email, setEmail] = useState('');
  const [claimNumber, setClaimNumber] = useState('');
  const [dateOfLoss, setDateOfLoss] = useState('');
  const [insuranceAgency, setInsuranceAgency] = useState('');
  const [insuranceContactName, setInsuranceContactName] = useState('');
  const [insuranceContactPhone, setInsuranceContactPhone] =
    useState(DEFAULT_PHONE);
  const [insuranceContactEmail, setInsuranceContactEmail] = useState('');
  const [adjusterName, setAdjusterName] = useState('');
  const [adjusterContactName, setAdjusterContactName] = useState('');
  const [adjusterContactPhone, setAdjusterContactPhone] =
    useState(DEFAULT_PHONE);
  const [adjusterContactEmail, setAdjusterContactEmail] = useState('');
  const [notes, setNotes] = useState<MockNote[]>([]);
  const [newNoteText, setNewNoteText] = useState('');
  const [status, setStatus] = useState('InProgress');

  // Handle mode toggle - clear form when switching to create mode
  useEffect(() => {
    if (!isEditMode) {
      setSelectedProjectId('');
      setSelectedProject(null);
      setSearchQuery('');
      setCustomerName('');
      setAddress(DEFAULT_ADDRESS);
      setPhone(DEFAULT_PHONE);
      setEmail('');
      setClaimNumber('');
      setDateOfLoss('');
      setInsuranceAgency('');
      setInsuranceContactName('');
      setInsuranceContactPhone(DEFAULT_PHONE);
      setInsuranceContactEmail('');
      setAdjusterName('');
      setAdjusterContactName('');
      setAdjusterContactPhone(DEFAULT_PHONE);
      setAdjusterContactEmail('');
      setNotes([]);
      setNewNoteText('');
      setStatus('In Progress');
    }
  }, [isEditMode]);

  // Handle project selection for editing
  useEffect(() => {
    if (isEditMode && selectedProjectId && projectsData) {
      const project = projectsData.projects.find(
        (p) => p.id === selectedProjectId,
      );
      if (project) {
        setSelectedProject(project);

        // Populate form with project data
        setCustomerName(project.customer_name || '');

        // Reconstruct address from components
        const addressParts = [
          project.address_line1,
          project.city,
          project.state && project.postal_code
            ? `${project.state} ${project.postal_code}`
            : project.state || project.postal_code,
        ].filter(Boolean);
        setAddress(addressParts.join(', ') || DEFAULT_ADDRESS);

        setPhone(project.provider_data?.phone || DEFAULT_PHONE);
        setEmail(project.provider_data?.email || '');
        setClaimNumber(project.claim_number || '');
        setDateOfLoss(project.date_of_loss || '');
        setInsuranceAgency(project.insurance_company || '');

        // Get insurance contact from provider_data
        const insuranceContact = project.provider_data?.insuranceContact;
        setInsuranceContactName(insuranceContact?.name || '');
        setInsuranceContactPhone(insuranceContact?.phone || DEFAULT_PHONE);
        setInsuranceContactEmail(insuranceContact?.email || '');

        setAdjusterName(project.adjuster_name || '');

        // Get adjuster contact from provider_data
        const adjusterContact = project.provider_data?.adjusterContact;
        setAdjusterContactName(adjusterContact?.name || '');
        setAdjusterContactPhone(adjusterContact?.phone || DEFAULT_PHONE);
        setAdjusterContactEmail(adjusterContact?.email || '');

        // Load notes from provider_data
        const projectNotes = project.provider_data?.notes || [];
        setNotes(Array.isArray(projectNotes) ? projectNotes : []);
        setStatus(project.status || 'In Progress');
      }
    }
  }, [isEditMode, selectedProjectId, projectsData]);

  // Feature flag check
  if (!env.PUBLIC_ENABLE_DEMO_PROJECT_CREATION) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <AlertCircle className="size-8 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Feature Not Available
          </h2>
          <p className="text-gray-600">
            Demo project creation is not enabled in this environment.
          </p>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();

    const projectData: MockProject = {
      customerName,
      address,
      phone,
      email,
      claimNumber,
      dateOfLoss,
      insuranceAgency,
      insuranceContactName,
      insuranceContactPhone,
      insuranceContactEmail,
      adjusterName,
      adjusterContactName,
      adjusterContactPhone,
      adjusterContactEmail,
      notes,
      status,
    };

    try {
      if (selectedProject) {
        // Update existing project
        await updateProjectMutation.mutateAsync({
          projectId: selectedProject.id,
          projectData,
        });
      } else {
        // Create new project
        await createProjectMutation.mutateAsync(projectData);
      }
      // Navigate to projects page on success
      navigate({ to: '/projects' });
    } catch (error) {
      console.error(
        `Failed to ${selectedProject ? 'update' : 'create'} project:`,
        error,
      );
    }
  };

  const isFormValid = customerName.trim() && (!isEditMode || selectedProject);
  const isLoading =
    createProjectMutation.isPending || updateProjectMutation.isPending;

  return (
    <div className="flex h-full bg-white p-6">
      <div className="w-full max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="size-10 rounded-lg bg-gradient-to-br from-orange-400 to-pink-400 flex items-center justify-center">
                <Building2 className="size-6 text-white" />
              </div>
              <div className="flex-1">
                <CardTitle className="text-2xl">Demo Project Manager</CardTitle>
                <p className="text-sm text-gray-600 mt-1">
                  Create or edit projects (Mock mode only)
                </p>
              </div>
            </div>

            {/* Mode Toggle */}
            <div className="mt-6 space-y-4">
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant={!isEditMode ? 'default' : 'outline'}
                  onClick={() => setIsEditMode(false)}
                  className="flex-1"
                >
                  Create New
                </Button>
                <Button
                  type="button"
                  variant={isEditMode ? 'default' : 'outline'}
                  onClick={() => setIsEditMode(true)}
                  className="flex-1"
                >
                  Edit Existing
                </Button>
              </div>

              {/* Project Search - only shown in edit mode */}
              {isEditMode && (
                <div className="space-y-3">
                  <Label htmlFor="project-search">Search for a Project</Label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-400" />
                    <Input
                      id="project-search"
                      type="text"
                      placeholder="Search by name, address, phone, or claim number..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10"
                    />
                  </div>

                  {/* Search Results */}
                  {searchQuery && (
                    <div className="mt-2">
                      <p className="text-sm text-gray-600 mb-2">
                        {filteredProjects.length}{' '}
                        {filteredProjects.length === 1 ? 'result' : 'results'}{' '}
                        found
                      </p>
                      {filteredProjects.length > 0 ? (
                        <div className="space-y-2 max-h-[500px] overflow-y-auto border rounded-md">
                          {filteredProjects.map((project) => (
                            <button
                              key={project.id}
                              type="button"
                              onClick={() => {
                                setSelectedProjectId(project.id);
                                setSearchQuery('');
                              }}
                              className={`w-full text-left p-3 hover:bg-gray-50 border-b last:border-b-0 transition-colors ${
                                selectedProjectId === project.id
                                  ? 'bg-blue-50'
                                  : ''
                              }`}
                            >
                              <div className="font-medium text-sm">
                                {project.customer_name ||
                                  project.name ||
                                  project.id}
                              </div>
                              <div className="text-xs text-gray-500 mt-1">
                                {project.provider_data?.address && (
                                  <span>{project.provider_data.address}</span>
                                )}
                                {project.claim_number && (
                                  <span className="ml-2">
                                    • Claim: {project.claim_number}
                                  </span>
                                )}
                              </div>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500 p-3 border rounded-md">
                          No projects found matching &ldquo;{searchQuery}&rdquo;
                        </p>
                      )}
                    </div>
                  )}

                  {/* Selected Project Display */}
                  {selectedProject && !searchQuery && (
                    <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-sm">
                            {selectedProject.customer_name ||
                              selectedProject.name ||
                              selectedProject.id}
                          </p>
                          {selectedProject.provider_data?.address && (
                            <p className="text-xs text-gray-600 mt-1">
                              {selectedProject.provider_data.address}
                            </p>
                          )}
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setSelectedProjectId('');
                            setSelectedProject(null);
                          }}
                          className="text-xs"
                        >
                          Change
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-8">
              {/* Customer Information */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 mb-4">
                  <Building2 className="size-5 text-gray-500" />
                  <h3 className="text-lg font-semibold text-gray-900">
                    Customer Information
                  </h3>
                </div>

                <div className="space-y-4 pl-7">
                  <div className="space-y-2">
                    <Label htmlFor="customerName">
                      Customer Name <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="customerName"
                      value={customerName}
                      onChange={(e) => setCustomerName(e.target.value)}
                      placeholder="John Smith"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="address">Address</Label>
                    <Input
                      id="address"
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      placeholder="123 Main St, Austin, TX 78701"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone</Label>
                    <Input
                      id="phone"
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+1-555-0123"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="customer@gmail.com"
                    />
                  </div>
                </div>
              </div>

              {/* Claim Information */}
              <div className="border-t pt-6 space-y-4">
                <div className="flex items-center gap-2 mb-4">
                  <FileText className="size-5 text-gray-500" />
                  <h3 className="text-lg font-semibold text-gray-900">
                    Claim Information
                  </h3>
                </div>

                <div className="space-y-4 pl-7">
                  <div className="space-y-2">
                    <Label htmlFor="claimNumber">Claim Number</Label>
                    <Input
                      id="claimNumber"
                      value={claimNumber}
                      onChange={(e) => setClaimNumber(e.target.value)}
                      placeholder="CLM-2024-001"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="dateOfLoss">Date of Loss</Label>
                    <Input
                      id="dateOfLoss"
                      type="date"
                      value={dateOfLoss}
                      onChange={(e) => setDateOfLoss(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="insuranceAgency">Insurance Agency</Label>
                    <Input
                      id="insuranceAgency"
                      value={insuranceAgency}
                      onChange={(e) => setInsuranceAgency(e.target.value)}
                      placeholder="State Farm Insurance"
                    />
                  </div>
                </div>
              </div>

              {/* Insurance Contact */}
              <div className="border-t pt-6 space-y-4">
                <div className="flex items-center gap-2 mb-4">
                  <User className="size-5 text-gray-500" />
                  <h3 className="text-lg font-semibold text-gray-900">
                    Insurance Contact
                  </h3>
                </div>

                <div className="space-y-4 pl-7">
                  <div className="space-y-2">
                    <Label htmlFor="insuranceContactName">Contact Name</Label>
                    <Input
                      id="insuranceContactName"
                      value={insuranceContactName}
                      onChange={(e) => setInsuranceContactName(e.target.value)}
                      placeholder="Sarah Johnson"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="insuranceContactPhone">Contact Phone</Label>
                    <Input
                      id="insuranceContactPhone"
                      type="tel"
                      value={insuranceContactPhone}
                      onChange={(e) => setInsuranceContactPhone(e.target.value)}
                      placeholder="+1-555-0123"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="insuranceContactEmail">Contact Email</Label>
                    <Input
                      id="insuranceContactEmail"
                      type="email"
                      value={insuranceContactEmail}
                      onChange={(e) => setInsuranceContactEmail(e.target.value)}
                      placeholder="contact@insurance.com"
                    />
                  </div>
                </div>
              </div>

              {/* Adjuster Information */}
              <div className="border-t pt-6 space-y-4">
                <div className="flex items-center gap-2 mb-4">
                  <User className="size-5 text-gray-500" />
                  <h3 className="text-lg font-semibold text-gray-900">
                    Adjuster Information
                  </h3>
                </div>

                <div className="space-y-4 pl-7">
                  <div className="space-y-2">
                    <Label htmlFor="adjusterName">Adjuster Name</Label>
                    <Input
                      id="adjusterName"
                      value={adjusterName}
                      onChange={(e) => setAdjusterName(e.target.value)}
                      placeholder="Mike Williams"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="adjusterContactName">Contact Name</Label>
                    <Input
                      id="adjusterContactName"
                      value={adjusterContactName}
                      onChange={(e) => setAdjusterContactName(e.target.value)}
                      placeholder="Mike Williams"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="adjusterContactPhone">Contact Phone</Label>
                    <Input
                      id="adjusterContactPhone"
                      type="tel"
                      value={adjusterContactPhone}
                      onChange={(e) => setAdjusterContactPhone(e.target.value)}
                      placeholder="+1-555-0123"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="adjusterContactEmail">Contact Email</Label>
                    <Input
                      id="adjusterContactEmail"
                      type="email"
                      value={adjusterContactEmail}
                      onChange={(e) => setAdjusterContactEmail(e.target.value)}
                      placeholder="adjuster@insurance.com"
                    />
                  </div>
                </div>
              </div>

              {/* Project Details */}
              <div className="border-t pt-6 space-y-4">
                <div className="flex items-center gap-2 mb-4">
                  <FileText className="size-5 text-gray-500" />
                  <h3 className="text-lg font-semibold text-gray-900">
                    Project Details
                  </h3>
                </div>

                <div className="space-y-4 pl-7">
                  <div className="space-y-2">
                    <Label htmlFor="status">Status</Label>
                    <Select value={status} onValueChange={setStatus}>
                      <SelectTrigger id="status">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {STATUS_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Notes</Label>
                    <div className="space-y-3">
                      {/* Existing Notes */}
                      {notes.length > 0 && (
                        <div className="space-y-2">
                          {notes.map((note, index) => (
                            <div key={note.id || index} className="flex gap-2">
                              <Textarea
                                value={note.text}
                                onChange={(e) => {
                                  const updatedNotes = [...notes];
                                  updatedNotes[index] = {
                                    ...note,
                                    text: e.target.value,
                                  };
                                  setNotes(updatedNotes);
                                }}
                                placeholder="Note text..."
                                rows={2}
                                className="flex-1"
                              />
                              <Button
                                type="button"
                                variant="outline"
                                size="icon"
                                onClick={() => {
                                  const updatedNotes = notes.filter(
                                    (_, i) => i !== index,
                                  );
                                  setNotes(updatedNotes);
                                }}
                                className="shrink-0"
                              >
                                <Trash2 className="size-4" />
                              </Button>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Add New Note */}
                      <div className="flex gap-2">
                        <Textarea
                          value={newNoteText}
                          onChange={(e) => setNewNoteText(e.target.value)}
                          placeholder="Add a new note..."
                          rows={2}
                          className="flex-1"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() => {
                            if (newNoteText.trim()) {
                              setNotes([
                                { text: newNoteText.trim() },
                                ...notes,
                              ]);
                              setNewNoteText('');
                            }
                          }}
                          disabled={!newNoteText.trim()}
                          className="shrink-0"
                        >
                          <Plus className="size-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <div className="flex gap-3 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate({ to: '/projects' })}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={!isFormValid || isLoading}
                  className="flex-1"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="size-4 mr-2 animate-spin" />
                      {selectedProject ? 'Updating...' : 'Creating...'}
                    </>
                  ) : selectedProject ? (
                    'Update Project'
                  ) : (
                    'Create Project'
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
