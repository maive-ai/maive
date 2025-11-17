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
  const [selectedProvider, setSelectedProvider] = useState<CRMProvider | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingCredentials, setIsFetchingCredentials] = useState(true);
  const [isTesting, setIsTesting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(
    null
  );

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
    if (selectedProvider === CRMProvider.JobNimbus) {
      return {
        provider: CRMProvider.JobNimbus,
        credentials: {
          api_key: jobNimbusApiKey,
        },
      };
    } else {
      throw new Error('Unsupported CRM provider');
    }
  };

  const handleTestConnection = async () => {
    if (!selectedProvider) {
      toast.error('Please select a CRM provider');
      return;
    }

    setIsTesting(true);
    setTestResult(null);

    try {
      // First save the credentials
      const credentialsData = buildCredentialsData();
      await createCRMCredentials(credentialsData);

      // Then try to fetch jobs to test the connection
      const token = await getIdToken();
      if (!token) throw new Error('Not authenticated');

      const crmApi = new CRMApi(
        new Configuration({
          accessToken: token,
          basePath: env.PUBLIC_SERVER_URL,
          baseOptions: { withCredentials: true },
        })
      );

      // Test by fetching 1 job
      await crmApi.getAllJobsApiCrmJobsGet(1, 1);

      setTestResult('success');
      toast.success('Connection successful! Your credentials are valid.');
    } catch (error) {
      console.error('Test connection failed:', error);
      setTestResult('error');
      toast.error(
        error instanceof Error
          ? error.message
          : 'Connection failed. Please check your credentials.'
      );
    } finally {
      setIsTesting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedProvider) {
      toast.error('Please select a CRM provider');
      return;
    }

    // Prevent double submission
    if (isLoading) {
      console.log('[CRMCredentialsSettings] Already submitting, ignoring...');
      return;
    }

    console.log('[CRMCredentialsSettings] Starting save...');
    setIsLoading(true);

    try {
      const credentialsData = buildCredentialsData();
      console.log('[CRMCredentialsSettings] Calling createCRMCredentials with:', { provider: credentialsData.provider });

      const credentials = await createCRMCredentials(credentialsData);
      console.log('[CRMCredentialsSettings] Credentials saved successfully:', credentials.id);

      // Reset form and update existing credentials
      setJobNimbusApiKey('');
      setSelectedProvider(null);
      setTestResult(null);
      setExistingCredentials(credentials);
      setIsLoading(false);

      // Show success message
      toast.success('CRM credentials saved successfully! Refreshing...');

      // Close the modal first
      console.log('[CRMCredentialsSettings] Closing modal...');
      onSuccess?.();

      // Then refresh the page after a short delay
      setTimeout(() => {
        console.log('[CRMCredentialsSettings] Refreshing page...');
        window.location.reload();
      }, 300);
    } catch (error) {
      console.error('[CRMCredentialsSettings] Failed to save credentials:', error);
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
      setSelectedProvider(null);
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

    if (existingCredentials && !selectedProvider) {
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
            onClick={() => setSelectedProvider(CRMProvider.JobNimbus)}
            className="w-full"
          >
            Update Credentials
          </Button>
        </div>
      );
    }

    if (!selectedProvider) {
      return (
        <div className="space-y-4">
          <p className="text-sm font-medium">Choose your CRM provider:</p>
          <button
            onClick={() => setSelectedProvider(CRMProvider.JobNimbus)}
            className="flex flex-col items-center gap-4 p-6 border-2 border-gray-200 rounded-lg hover:border-primary-900 hover:bg-primary-50 transition-colors w-full"
          >
            <img
              src={jobNimbusLogo}
              alt="JobNimbus"
              className="h-12 object-contain"
            />
            <span className="font-medium">JobNimbus</span>
          </button>
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
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setSelectedProvider(null);
                setTestResult(null);
              }}
            >
              Cancel
            </Button>
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

          {testResult && (
            <div
              className={`p-3 rounded-lg text-sm ${
                testResult === 'success'
                  ? 'bg-green-50 text-green-800 border border-green-200'
                  : 'bg-red-50 text-red-800 border border-red-200'
              }`}
            >
              {testResult === 'success' ? (
                <p>✓ Connection successful! Your credentials are valid.</p>
              ) : (
                <p>
                  ✗ Connection failed. Please verify your credentials and try
                  again.
                </p>
              )}
            </div>
          )}

          <div className="flex justify-between items-center gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={handleTestConnection}
              disabled={isLoading || isTesting}
            >
              {isTesting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Test Connection
            </Button>
            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setSelectedProvider(null);
                  setTestResult(null);
                }}
                disabled={isLoading || isTesting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading || isTesting}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save Credentials
              </Button>
            </div>
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
