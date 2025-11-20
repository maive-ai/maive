import * as DialogPrimitive from '@radix-ui/react-dialog';
import { Code, Phone, Unplug } from 'lucide-react';
import { useEffect, useState } from 'react';

import { useIsMaiveUser } from '@/auth';
import { CRMCredentialsSettings } from '@/components/settings/CRMCredentialsSettings';
import { TwilioConfigSettings } from '@/components/settings/TwilioConfigSettings';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';


interface SettingsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type SettingsTab = 'crm' | 'twilio' | 'developer';

export function SettingsModal({ open, onOpenChange }: SettingsModalProps) {
  const isMaiveUser = useIsMaiveUser();
  const [activeTab, setActiveTab] = useState<SettingsTab>('crm');
  const [companyName, setCompanyName] = useState<string>('');

  useEffect(() => {
    const savedCompanyName = localStorage.getItem('companyName');
    if (savedCompanyName) {
      setCompanyName(savedCompanyName);
    }
  }, [open]);

  const handleSave = (): void => {
    localStorage.setItem('companyName', companyName);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/30 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <DialogContent className="sm:max-w-[900px] max-h-[80vh] p-0 bg-primary-50 backdrop-blur-md shadow-2xl">
          <div className="flex h-full max-h-[80vh]">
            {/* Sidebar */}
            <div className="w-64 bg-primary-200 p-4 space-y-1 rounded-l-lg">
              <div className="px-3 py-2 mb-4">
                <DialogTitle className="text-lg font-semibold">Settings</DialogTitle>
                <DialogDescription className="text-sm">
                  Configure your application
                </DialogDescription>
              </div>

              <button
                onClick={() => setActiveTab('crm')}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === 'crm'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                <Unplug className="h-4 w-4" />
                CRM Integrations
              </button>

              {isMaiveUser && (
                <button
                  onClick={() => setActiveTab('twilio')}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeTab === 'twilio'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  }`}
                >
                  <Phone className="h-4 w-4" />
                  Twilio Phone
                </button>
              )}

              {isMaiveUser && (
                <button
                  onClick={() => setActiveTab('developer')}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeTab === 'developer'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  }`}
                >
                  <Code className="h-4 w-4" />
                  Developer
                </button>
              )}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {activeTab === 'crm' && (
                <CRMCredentialsSettings onSuccess={() => onOpenChange(false)} />
              )}

              {activeTab === 'twilio' && (
                <TwilioConfigSettings onSuccess={() => onOpenChange(false)} />
              )}

              {activeTab === 'developer' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-medium">Developer Settings</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Configure developer-specific options
                    </p>
                  </div>

                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="company-name">Company Name</Label>
                      <Input
                        id="company-name"
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        placeholder="Enter company name"
                      />
                    </div>
                    <div className="flex justify-end gap-3 pt-4">
                      <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Cancel
                      </Button>
                      <Button onClick={handleSave}>Save</Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </DialogPrimitive.Portal>
    </Dialog>
  );
}

