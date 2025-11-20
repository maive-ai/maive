import { CRMProvider } from '@maive/api/client';
import jobNimbusLogo from '@maive/brand/logos/integrations/jobnimbus/jobnimbus_logo.png';
import serviceTitanLogo from '@maive/brand/logos/integrations/servicetitan/ServiceTitan_Logo_Black_2.png';
import { Loader2, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import { useIsMaiveUser } from '@/auth';
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

interface CRMCredentialsSettingsProps {
  onSuccess?: () => void;
}

export function CRMCredentialsSettings({
  onSuccess,
}: CRMCredentialsSettingsProps) {
  const isMaiveUser = useIsMaiveUser();
  const [existingCredentials, setExistingCredentials] =
    useState<CRMCredentials | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<CRMProvider | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingCredentials, setIsFetchingCredentials] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);

  // JobNimbus state
  const [jobNimbusApiKey, setJobNimbusApiKey] = useState('');

  // ServiceTitan state
  const [serviceTitanTenantId, setServiceTitanTenantId] = useState('');
  const [serviceTitanClientId, setServiceTitanClientId] = useState('');
  const [serviceTitanClientSecret, setServiceTitanClientSecret] = useState('');
  const [serviceTitanAppKey, setServiceTitanAppKey] = useState('');

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
    if (selectedProvider === CRMProvider.Mock) {
      return {
        provider: CRMProvider.Mock,
        credentials: {},
      };
    } else if (selectedProvider === CRMProvider.JobNimbus) {
      return {
        provider: CRMProvider.JobNimbus,
        credentials: {
          api_key: jobNimbusApiKey,
        },
      };
    } else if (selectedProvider === CRMProvider.ServiceTitan) {
      return {
        provider: CRMProvider.ServiceTitan,
        credentials: {
          tenant_id: serviceTitanTenantId,
          client_id: serviceTitanClientId,
          client_secret: serviceTitanClientSecret,
          app_key: serviceTitanAppKey,
        },
      };
    } else {
      throw new Error('Please select a CRM provider');
    }
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
      console.log(
        '[CRMCredentialsSettings] Calling createCRMCredentials with:',
        { provider: credentialsData.provider },
      );

      const credentials = await createCRMCredentials(credentialsData);
      console.log(
        '[CRMCredentialsSettings] Credentials saved successfully:',
        credentials.id,
      );

      // Reset form and update existing credentials
      setJobNimbusApiKey('');
      setServiceTitanTenantId('');
      setServiceTitanClientId('');
      setServiceTitanClientSecret('');
      setServiceTitanAppKey('');
      setSelectedProvider(null);
      setExistingCredentials(credentials);
      setIsLoading(false);

      // Show success message
      toast.success('✓ Credentials saved successfully!');

      // Notify parent component
      onSuccess?.();
    } catch (error) {
      console.error(
        '[CRMCredentialsSettings] Failed to save or test credentials:',
        error,
      );
      setIsLoading(false);

      // Log the full error for debugging
      if (error instanceof Error) {
        console.error('[CRMCredentialsSettings] Error details:', {
          message: error.message,
          stack: error.stack,
          name: error.name,
        });
      }

      toast.error(
        error instanceof Error ? error.message : 'Failed to save credentials',
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
      onSuccess?.();
    } catch (error) {
      console.error('Failed to delete credentials:', error);
      toast.error(
        error instanceof Error ? error.message : 'Failed to delete credentials',
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
          <p className="text-sm text-muted-foreground">
            Loading your CRM configuration...
          </p>
        </div>
      );
    }

    if (existingCredentials && !selectedProvider) {
      const isJobNimbus =
        existingCredentials.provider === CRMProvider.JobNimbus;
      return (
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <img
                  src={isJobNimbus ? jobNimbusLogo : serviceTitanLogo}
                  alt={isJobNimbus ? 'JobNimbus' : 'ServiceTitan'}
                  className="h-10 object-contain"
                />
                <div>
                  <p className="font-medium">
                    {isJobNimbus ? 'JobNimbus' : 'ServiceTitan'}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {isJobNimbus
                      ? 'API Key: ••••••••••••'
                      : 'Credentials: ••••••••••••'}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Connected{' '}
                    {new Date(
                      existingCredentials.created_at,
                    ).toLocaleDateString()}
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
            onClick={() =>
              setSelectedProvider(existingCredentials.provider as CRMProvider)
            }
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
          <div className={`grid gap-4 ${isMaiveUser ? 'grid-cols-3' : 'grid-cols-2'}`}>
            <button
              onClick={() => setSelectedProvider(CRMProvider.JobNimbus)}
              className="flex flex-col items-center gap-4 p-6 border-2 border-gray-200 rounded-lg hover:border-primary-900 hover:bg-primary-50 transition-colors"
            >
              <img
                src={jobNimbusLogo}
                alt="JobNimbus"
                className="h-12 object-contain"
              />
              <span className="font-medium">JobNimbus</span>
            </button>

            <button
              onClick={() => setSelectedProvider(CRMProvider.ServiceTitan)}
              className="flex flex-col items-center gap-4 p-6 border-2 border-gray-200 rounded-lg hover:border-primary-900 hover:bg-primary-50 transition-colors"
            >
              <img
                src={serviceTitanLogo}
                alt="ServiceTitan"
                className="h-12 object-contain"
              />
              <span className="font-medium">ServiceTitan</span>
            </button>

            {isMaiveUser && (
              <button
                onClick={() => setSelectedProvider(CRMProvider.Mock)}
                className="flex flex-col items-center gap-4 p-6 border-2 border-gray-200 rounded-lg hover:border-primary-900 hover:bg-primary-50 transition-colors"
              >
                <div className="h-12 flex items-center justify-center">
                  <span className="text-2xl">🧪</span>
                </div>
                <span className="font-medium">Mock (Dev)</span>
              </button>
            )}
          </div>
        </div>
      );
    }

    const getProviderDisplayName = (provider: CRMProvider): string => {
      switch (provider) {
        case CRMProvider.Mock:
          return 'Mock (Dev)';
        case CRMProvider.JobNimbus:
          return 'JobNimbus';
        case CRMProvider.ServiceTitan:
          return 'ServiceTitan';
        default:
          return 'Unknown';
      }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="flex items-center gap-4 pb-4 border-b">
          {selectedProvider === CRMProvider.Mock ? (
            <div className="h-10 flex items-center">
              <span className="text-3xl">🧪</span>
            </div>
          ) : (
            <img
              src={
                selectedProvider === CRMProvider.JobNimbus
                  ? jobNimbusLogo
                  : serviceTitanLogo
              }
              alt={getProviderDisplayName(selectedProvider)}
              className="h-10 object-contain"
            />
          )}
            <div className="flex-1">
            <p className="font-medium">
              {getProviderDisplayName(selectedProvider)}
            </p>
              <p className="text-sm text-muted-foreground">
              {selectedProvider === CRMProvider.Mock
                ? 'Testing provider with hardcoded data'
                : 'Configure your credentials'}
              </p>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setSelectedProvider(null);
                setJobNimbusApiKey('');
                setServiceTitanTenantId('');
                setServiceTitanClientId('');
                setServiceTitanClientSecret('');
                setServiceTitanAppKey('');
              }}
            >
              Change
            </Button>
          </div>

        {selectedProvider === CRMProvider.Mock ? (
          <div className="space-y-4">
            <div className="rounded-lg bg-amber-50 border border-amber-200 p-4">
              <p className="text-sm text-amber-900">
                <strong>Developer Mode:</strong> Mock provider uses hardcoded test
                data. No credentials required.
              </p>
            </div>
          </div>
        ) : selectedProvider === CRMProvider.JobNimbus ? (
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
                Find or create an API key by following the instructions in the{' '}
                <a
                  href="https://support.jobnimbus.com/how-do-i-create-an-api-key"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-900 underline"
                >
                  JobNimbus documentation
                </a>
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="tenant-id">Tenant ID *</Label>
                <Input
                  id="tenant-id"
                  value={serviceTitanTenantId}
                  onChange={(e) => setServiceTitanTenantId(e.target.value)}
                  placeholder="Enter your ServiceTitan tenant ID"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="client-id">Client ID *</Label>
                <Input
                  id="client-id"
                  value={serviceTitanClientId}
                  onChange={(e) => setServiceTitanClientId(e.target.value)}
                  placeholder="Enter your client ID"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="client-secret">Client Secret *</Label>
                <Input
                  id="client-secret"
                  type="password"
                  value={serviceTitanClientSecret}
                  onChange={(e) => setServiceTitanClientSecret(e.target.value)}
                  placeholder="Enter your client secret"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="app-key">App Key *</Label>
                <Input
                  id="app-key"
                  type="password"
                  value={serviceTitanAppKey}
                  onChange={(e) => setServiceTitanAppKey(e.target.value)}
                  placeholder="Enter your app key"
                  required
                />
              </div>

              <p className="text-xs text-muted-foreground">
                Find your credentials in ServiceTitan Settings → Integrations →
                API Application Access
              </p>
            </div>
          )}

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
