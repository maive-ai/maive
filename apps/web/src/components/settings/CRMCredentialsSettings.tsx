import { Configuration, CRMApi, CRMProvider } from '@maive/api/client';
import { Loader2 } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';

import { getIdToken } from '@/auth';
import {
  createCRMCredentials,
  type CRMCredentialsCreate,
} from '@/clients/credentials';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { env } from '@/env';

// Import logos
import jobNimbusLogo from '@maive/brand/logos/integrations/jobnimbus/jobnimbus_logo.png';
import serviceTitanLogo from '@maive/brand/logos/integrations/servicetitan/ServiceTitan_Logo_Black_2.png';

interface CRMCredentialsSettingsProps {
  onSuccess?: () => void;
}

export function CRMCredentialsSettings({
  onSuccess,
}: CRMCredentialsSettingsProps) {
  const [selectedProvider, setSelectedProvider] = useState<CRMProvider | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(
    null
  );

  // JobNimbus state
  const [jobNimbusApiKey, setJobNimbusApiKey] = useState('');

  // ServiceTitan state
  const [serviceTitanTenantId, setServiceTitanTenantId] = useState('');
  const [serviceTitanClientId, setServiceTitanClientId] = useState('');
  const [serviceTitanClientSecret, setServiceTitanClientSecret] = useState('');
  const [serviceTitanAppKey, setServiceTitanAppKey] = useState('');

  const buildCredentialsData = (): CRMCredentialsCreate => {
    if (selectedProvider === CRMProvider.JobNimbus) {
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

    setIsLoading(true);

    try {
      const credentialsData = buildCredentialsData();
      await createCRMCredentials(credentialsData);

      toast.success('CRM credentials saved successfully!');

      // Reset form
      setJobNimbusApiKey('');
      setServiceTitanTenantId('');
      setServiceTitanClientId('');
      setServiceTitanClientSecret('');
      setServiceTitanAppKey('');
      setSelectedProvider(null);
      setTestResult(null);

      onSuccess?.();
    } catch (error) {
      console.error('Failed to save credentials:', error);
      toast.error(
        error instanceof Error ? error.message : 'Failed to save credentials'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium">CRM Integration</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Connect your CRM to enable seamless data synchronization
        </p>
      </div>

      {!selectedProvider ? (
        <div className="space-y-4">
          <p className="text-sm font-medium">Choose your CRM provider:</p>
          <div className="grid grid-cols-2 gap-4">
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
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="flex items-center gap-4 pb-4 border-b">
            <img
              src={
                selectedProvider === CRMProvider.JobNimbus
                  ? jobNimbusLogo
                  : serviceTitanLogo
              }
              alt={selectedProvider}
              className="h-10 object-contain"
            />
            <div className="flex-1">
              <p className="font-medium">
                {selectedProvider === CRMProvider.JobNimbus
                  ? 'JobNimbus'
                  : 'ServiceTitan'}
              </p>
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
              Change
            </Button>
          </div>

          {selectedProvider === CRMProvider.JobNimbus && (
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
                  Find or create an API key by following the instructions in the <a href="https://docs.jobnimbus.com/docs/api-key" target="_blank" rel="noopener noreferrer">JobNimbus documentation</a>
                </p>
              </div>
            </div>
          )}

          {selectedProvider === CRMProvider.ServiceTitan && (
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
      )}
    </div>
  );
}
