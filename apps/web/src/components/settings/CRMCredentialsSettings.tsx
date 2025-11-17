import { Configuration, CRMApi, CRMProvider } from '@maive/api/client';
import { Loader2, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { getIdToken } from '@/auth';
import {
  createCRMCredentials,
  deleteCRMCredentials,
  getCRMCredentials,
  type CRMCredentials,
  type CRMCredentialsCreate,
} from '@/clients/credentials';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { env } from '@/env';

// Import logos
import jobNimbusLogo from '@maive/brand/logos/integrations/jobnimbus/jobnimbus_logo.png';

interface CRMCredentialsSettingsProps {
  onSuccess?: () => void;
}

export function CRMCredentialsSettings({
  onSuccess,
}: CRMCredentialsSettingsProps) {
  const [existingCredentials, setExistingCredentials] = useState<CRMCredentials | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingCredentials, setIsFetchingCredentials] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);

  // JobNimbus state
  const [jobNimbusApiKey, setJobNimbusApiKey] = useState('');

  // Load existing credentials on mount
  useEffect(() => {
    let mounted = true;

    const loadCredentials = async () => {
      try {
        const credentials = await getCRMCredentials();
        if (mounted) {
          // Set both states together to ensure they update in same render cycle
          setExistingCredentials(credentials);
          setIsFetchingCredentials(false);
        }
      } catch {
        // No credentials found or error fetching - that's okay
        console.log('No existing credentials found');
        if (mounted) {
          setIsFetchingCredentials(false);
        }
      }
    };

    loadCredentials();

    return () => {
      mounted = false;
    };
  }, []);

  const buildCredentialsData = (): CRMCredentialsCreate => {
    return {
      provider: CRMProvider.JobNimbus,
      credentials: {
        api_key: jobNimbusApiKey,
      },
    };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Prevent double submission
    if (isLoading) {
      console.log('[CRMCredentialsSettings] Already submitting, ignoring...');
      return;
    }

    console.log('[CRMCredentialsSettings] Starting save...');
    setIsLoading(true);

    try {
      // Step 1: Save credentials
      const credentialsData = buildCredentialsData();
      console.log('[CRMCredentialsSettings] Calling createCRMCredentials with:', { provider: credentialsData.provider });

      const credentials = await createCRMCredentials(credentialsData);
      console.log('[CRMCredentialsSettings] Credentials saved successfully:', credentials.id);

      // Reset form and update existing credentials
      setJobNimbusApiKey('');
      setIsEditing(false);
      setExistingCredentials(credentials);
      setIsLoading(false);

      // Show success message
      toast.success('✓ Credentials saved successfully! Refreshing...');

      // Store that modal should stay open after refresh
      sessionStorage.setItem('keepSettingsModalOpen', 'true');

      // Refresh the page after a short delay
      setTimeout(() => {
        console.log('[CRMCredentialsSettings] Refreshing page...');
        window.location.reload();
      }, 1000);
    } catch (error) {
      console.error('[CRMCredentialsSettings] Failed to save or test credentials:', error);
      setIsLoading(false);

      // Log the full error for debugging
      if (error instanceof Error) {
        console.error('[CRMCredentialsSettings] Error details:', {
          message: error.message,
          stack: error.stack,
          name: error.name
        });
      }

      toast.error(
        error instanceof Error ? error.message : 'Failed to save credentials'
      );
    }
  };

  const handleDelete = async () => {
    if (!existingCredentials) return;

    setIsDeleting(true);
    try {
      await deleteCRMCredentials();
      toast.success('CRM credentials deleted successfully!');
      setExistingCredentials(null);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to delete credentials:', error);
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete credentials'
      );
    } finally {
      setIsDeleting(false);
    }
  };

  // Determine what to render
  const renderContent = () => {
    if (isFetchingCredentials) {
      return (
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary-900" />
          <p className="text-sm text-muted-foreground">Loading your CRM configuration...</p>
        </div>
      );
    }

    if (existingCredentials && !isEditing) {
      return (
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <img
                  src={jobNimbusLogo}
                  alt="JobNimbus"
                  className="h-10 object-contain"
                />
                <div>
                  <p className="font-medium">JobNimbus</p>
                  <p className="text-sm text-muted-foreground">
                    API Key: ••••••••••••
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Connected {new Date(existingCredentials.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleDelete}
                disabled={isDeleting}
                className="text-red-600 hover:text-red-700 hover:bg-red-50"
              >
                {isDeleting ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Trash2 className="h-5 w-5" />
                )}
              </Button>
            </div>
          </div>
          <Button
            variant="outline"
            onClick={() => setIsEditing(true)}
            className="w-full"
          >
            Update Credentials
          </Button>
        </div>
      );
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="flex items-center gap-4 pb-4 border-b">
            <img
              src={jobNimbusLogo}
              alt="JobNimbus"
              className="h-10 object-contain"
            />
            <div className="flex-1">
              <p className="font-medium">JobNimbus</p>
              <p className="text-sm text-muted-foreground">
                Configure your credentials
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="api-key">API Key *</Label>
              <Input
                id="api-key"
                type="password"
                value={jobNimbusApiKey}
                onChange={(e) => setJobNimbusApiKey(e.target.value)}
                placeholder="Enter your JobNimbus API key"
                required
              />
              <p className="text-xs text-muted-foreground">
                Find or create an API key by following the instructions in the <a href="https://docs.jobnimbus.com/docs/api-key" target="_blank" rel="noopener noreferrer" className="text-primary-900 hover:underline">JobNimbus documentation</a>
              </p>
            </div>
          </div>

          <div className="flex justify-end pt-4">
            <Button type="submit" disabled={isLoading} className="min-w-[180px]">
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Credentials
            </Button>
          </div>
        </form>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium">CRM Integration</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Connect your CRM to enable seamless data synchronization
        </p>
      </div>

      {renderContent()}
    </div>
  );
}
