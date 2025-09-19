import {
    CheckCircle,
    Clock,
    DollarSign,
    FileText,
    XCircle,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './card';

// import { type CustomerDetails } from '@/clients/customer-crm';

// Placeholder type for CustomerDetails
interface CustomerDetails {
  claimStatus?: string;
  notes?: string;
}

interface ClaimStatusStepperProps {
  customer: CustomerDetails;
}

// Define the claim status flow
const CLAIM_STATUS_STEPS = [
  {
    key: 'pending_review',
    label: 'Pending Review',
    icon: Clock,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-100',
    borderColor: 'border-yellow-200',
  },
  {
    key: 'needs_documents',
    label: 'Needs Documents',
    icon: FileText,
    color: 'text-orange-600',
    bgColor: 'bg-orange-100',
    borderColor: 'border-orange-200',
  },
  {
    key: 'approved',
    label: 'Approved',
    icon: CheckCircle,
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    borderColor: 'border-green-200',
  },
  {
    key: 'denied',
    label: 'Denied',
    icon: XCircle,
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    borderColor: 'border-red-200',
  },
  {
    key: 'payment_issued',
    label: 'Payment Issued',
    icon: DollarSign,
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    borderColor: 'border-green-200',
  },
];

function getCurrentStepIndex(status?: string): number {
  if (!status) return 0;
  const index = CLAIM_STATUS_STEPS.findIndex((step) => step.key === status);
  return index >= 0 ? index : 0;
}

function getStepStatus(
  stepIndex: number,
  currentStepIndex: number,
  currentStatus?: string,
) {
  if (stepIndex < currentStepIndex) return 'completed';
  if (stepIndex === currentStepIndex) return 'current';
  return 'upcoming';
}

export function ClaimStatusStepper({ customer }: ClaimStatusStepperProps) {
  const currentStepIndex = getCurrentStepIndex(customer.claimStatus);
  const currentStep = CLAIM_STATUS_STEPS[currentStepIndex];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Claim Status</CardTitle>
      </CardHeader>
      <CardContent>
        {/* No Status Message - show only this when no claim status */}
        {!customer.claimStatus ? (
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-600">
                No claim status available
              </span>
            </div>
          </div>
        ) : (
          <>
            {/* Stepper Steps - only show when claim status exists */}
            <div className="flex items-center justify-between">
              {CLAIM_STATUS_STEPS.map((step, index) => {
                const status = getStepStatus(
                  index,
                  currentStepIndex,
                  customer.claimStatus,
                );
                const Icon = step.icon;
                const isCompleted = status === 'completed';
                const isCurrent = status === 'current';

                return (
                  <div
                    key={step.key}
                    className="flex flex-col items-center flex-1"
                  >
                    {/* Step Circle */}
                    <div
                      className={`
                        w-10 h-10 rounded-full flex items-center justify-center mb-2 transition-all duration-200
                        ${
                          isCompleted
                            ? 'bg-green-500 text-white'
                            : isCurrent
                              ? `${step.bgColor} ${step.color} border-2 ${step.borderColor}`
                              : 'bg-gray-100 text-gray-400'
                        }
                      `}
                    >
                      {isCompleted ? (
                        <CheckCircle className="w-5 h-5" />
                      ) : (
                        <Icon className="w-5 h-5" />
                      )}
                    </div>

                    {/* Step Label */}
                    <div className="text-center">
                      <p
                        className={`
                          text-xs font-medium transition-colors duration-200
                          ${
                            isCurrent || isCompleted
                              ? 'text-gray-900'
                              : 'text-gray-500'
                          }
                        `}
                      >
                        {step.label}
                      </p>
                      {isCurrent && customer.claimStatus && (
                        <p className="text-xs text-gray-500 mt-1">
                          Current Status
                        </p>
                      )}
                    </div>

                    {/* Connector Line */}
                    {index < CLAIM_STATUS_STEPS.length - 1 && (
                      <div
                        className={`
                          absolute top-5 left-1/2 w-full h-0.5 -z-10 transition-colors duration-200
                          ${isCompleted ? 'bg-green-500' : 'bg-gray-200'}
                        `}
                        style={{
                          width: 'calc(100% - 2.5rem)',
                          left: 'calc(50% + 1.25rem)',
                        }}
                      />
                    )}
                  </div>
                );
              })}
            </div>

            {/* Current Status Details */}
            {currentStep && customer.claimStatus && (
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2">
                  <currentStep.icon
                    className={`w-4 h-4 ${currentStep.color}`}
                  />
                  <span className="text-sm font-medium text-gray-900">
                    Current Status: {currentStep.label}
                  </span>
                </div>
                {customer.notes && (
                  <p className="text-sm text-gray-600 mt-2">{customer.notes}</p>
                )}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
