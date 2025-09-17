import { createFileRoute } from '@tanstack/react-router';
import { Clock } from 'lucide-react';
import { useState } from 'react';
import type { Value as E164Number } from 'react-phone-number-input';

import {
  pollForJobCompletion,
  startAiJob,
  type AiJobResult,
} from '@/clients/gemini-ai';
import {
  startPhotoAnalysis,
  type StartPhotoAnalysisRequest,
} from '@/clients/photo-analysis';
import { useCreateOutboundCall } from '@/clients/voice-ai';
import { FileUpload } from '@/components/nodes/FileUpload';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

export const Route = createFileRoute('/_authed/phone-input')({
  component: PhoneInputPage,
});

interface PhotoAnalysisResult {
  name: string;
  company: string;
  phone_number: string;
  email?: string;
  title?: string;
}

interface AnalysisJob {
  job_id: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  s3_key: string;
  result?: PhotoAnalysisResult;
  call_id?: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

function PhoneInputPage() {
  // Phone input state
  const [phoneNumber, setPhoneNumber] = useState<E164Number | undefined>();

  // File upload state
  const [aiResults, setAiResults] = useState<string | null>(null);

  // Photo analysis state
  const [photoAnalysisMode, setPhotoAnalysisMode] = useState(true);
  const [isAnalyzingPhoto, setIsAnalyzingPhoto] = useState(false);
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const createCallMutation = useCreateOutboundCall();

  // Default prompt for image analysis
  const DEFAULT_PROMPT =
    "\
    You've been provided a business card from a roofing company. \
    Extract all the information from the business card. \
    Additionally search the internet for any additional information about the company and the person on the business card. \
    Return a detailed description of the company and the person on the business card.";

  // Handle successful file upload
  const handleUploadSuccess = async (key: string) => {
    console.log('handleUploadSuccess called with key:', key);
    console.log('Key type:', typeof key, 'Key value:', JSON.stringify(key));

    if (
      key &&
      key !== '' &&
      key.trim() !== '' &&
      key !== 'undefined' &&
      key !== 'null'
    ) {
      if (photoAnalysisMode) {
        // Start photo analysis for contact extraction
        console.log('Starting photo analysis for key:', key);
        await startPhotoAnalysisJob(key);
      } else {
        // Start regular AI processing
        console.log('Starting AI processing for key:', key);
        await processImageWithAI(key);
      }
    } else {
      // Clear results if file is cleared or key is invalid
      console.log('No valid key provided, clearing results. Key was:', key);
      setAiResults(null);
      setAnalysisJob(null);
      setAnalysisError(null);
    }
  };

  // Process uploaded image with Gemini AI
  const processImageWithAI = async (s3Key: string) => {
    console.log('processImageWithAI called with s3Key:', s3Key);

    // Validate s3Key before processing
    if (!s3Key || s3Key.trim() === '') {
      console.error('Invalid s3Key provided to processImageWithAI:', s3Key);
      return;
    }

    setAiResults(null);

    try {
      console.log(
        'Calling startAiJob with s3Key:',
        s3Key,
        'prompt length:',
        DEFAULT_PROMPT.length,
      );

      // Additional validation before calling startAiJob
      if (!s3Key || s3Key.length === 0) {
        throw new Error('S3 key is empty or invalid');
      }

      if (DEFAULT_PROMPT.length === 0) {
        throw new Error('Prompt is empty');
      }

      console.log('✅ Pre-validation passed - s3Key and prompt are valid');

      // Log the exact parameters being passed to startAiJob
      console.log('📤 Calling startAiJob with parameters:');
      console.log('  - s3Key:', JSON.stringify(s3Key));
      console.log('  - prompt length:', DEFAULT_PROMPT.length);
      console.log('  - workflowId:', undefined);

      // Start AI job
      const jobResult = await startAiJob(s3Key, DEFAULT_PROMPT);

      console.log('📥 startAiJob result:', jobResult);

      if (jobResult.success && jobResult.jobId) {
        const jobId = jobResult.jobId;
        console.log('Started AI job with ID:', jobId);

        // Poll for completion
        const finalResult = await pollForJobCompletion(
          jobId,
          (updateResult: AiJobResult) => {
            // Optional: Add progress updates here
            console.log('AI processing update:', updateResult.status);
          },
        );

        console.log('Final AI result:', finalResult);

        if (finalResult.success && finalResult.response) {
          setAiResults(finalResult.response);
          console.log('AI processing completed successfully');
        } else {
          console.error('AI processing failed:', finalResult.message);
        }
      } else {
        console.error(
          'Failed to start AI job:',
          jobResult.message,
          jobResult.error,
        );
      }
    } catch (error) {
      console.error('Error processing image with AI:', error);
    } finally {
      // Processing complete
    }
  };

  // Start photo analysis for contact extraction
  const startPhotoAnalysisJob = async (s3Key: string) => {
    console.log('startPhotoAnalysisJob called with s3Key:', s3Key);

    setIsAnalyzingPhoto(true);
    setAnalysisError(null);

    try {
      // Prepare request
      const request: StartPhotoAnalysisRequest = {
        s3_key: s3Key,
        user_email: 'user@example.com', // This should come from auth context
      };

      // Call the start photo analysis API
      const result = await startPhotoAnalysis(request);

      // Create initial job state
      const job: AnalysisJob = {
        job_id: result.job_id,
        status: result.status as
          | 'PENDING'
          | 'PROCESSING'
          | 'COMPLETED'
          | 'FAILED',
        s3_key: s3Key,
        created_at: new Date().toISOString(),
      };

      setAnalysisJob(job);

      // Start polling for results
      pollPhotoAnalysisStatus(result.job_id);
    } catch (err) {
      setAnalysisError(
        err instanceof Error ? err.message : 'Failed to start analysis',
      );
      setIsAnalyzingPhoto(false);
    }
  };

  // Poll photo analysis status
  const pollPhotoAnalysisStatus = async (jobId: string) => {
    // For now, just show that the process was initiated successfully
    // In the future, this would poll for real status updates
    console.log('Photo analysis job started with ID:', jobId);
    console.log(
      'Process initiated successfully - analysis is running in the background',
    );

    // Update job status to show it's processing
    setAnalysisJob((prev) =>
      prev
        ? {
            ...prev,
            status: 'PROCESSING',
          }
        : null,
    );

    setIsAnalyzingPhoto(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (phoneNumber) {
      const callMetadata: any = {
        source: 'phone-input-page',
        assistant_name: 'Riley',
      };

      // Include AI analysis results if available
      if (aiResults) {
        callMetadata.image_analysis = aiResults;
      }

      createCallMutation.mutate({
        phone_number: phoneNumber,
        claim_number: 'CLM20251234',
        metadata: callMetadata,
      });
    }
  };

  return (
    <div className="container mx-auto max-w-4xl py-8">
      <div className="space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900">Voice AI Call</h1>
          <p className="text-gray-600 mt-2">
            {photoAnalysisMode
              ? 'Upload a photo to extract contact information and initiate a call automatically'
              : 'Upload an image and enter a phone number to start an AI-powered call'}
          </p>
        </div>

        {/* Mode Toggle */}
        <div className="flex justify-center">
          <div className="bg-gray-100 p-1 rounded-lg">
            <button
              onClick={() => setPhotoAnalysisMode(false)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                !photoAnalysisMode
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Manual Entry
            </button>
            <button
              onClick={() => setPhotoAnalysisMode(true)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                photoAnalysisMode
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Photo Analysis
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {photoAnalysisMode ? (
            // Photo Analysis Mode - Show only upload card
            <div className="max-w-2xl mx-auto">
              <Card>
                <CardHeader>
                  <CardTitle>Upload Photo</CardTitle>
                  <CardDescription>
                    Upload a clear photo of a business card or contact
                    information
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <FileUpload
                    onUploadSuccess={handleUploadSuccess}
                    onUploadStateChange={() => {}}
                  />

                  {/* Photo Analysis Status */}
                  {isAnalyzingPhoto && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-4">
                      <p className="text-blue-800 text-sm">
                        🔍 Extracting contact information from photo...
                      </p>
                    </div>
                  )}

                  {/* Analysis Success */}
                  {analysisJob?.status === 'PROCESSING' && (
                    <div className="p-4 bg-blue-50 rounded-lg mt-4">
                      <div className="flex items-center">
                        <Clock className="w-5 h-5 mr-2 text-blue-600" />
                        <span className="text-sm font-medium text-blue-800">
                          Photo analysis initiated successfully!
                        </span>
                      </div>
                      <p className="text-xs text-blue-700 mt-1">
                        Your photo is being analyzed. The system will extract
                        contact information and initiate a call automatically.
                      </p>
                    </div>
                  )}

                  {/* Analysis Error */}
                  {analysisError && (
                    <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg mt-4">
                      <p className="text-sm text-red-700">{analysisError}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          ) : (
            // Manual Entry Mode - Show only call details card
            <div className="max-w-2xl mx-auto">
              <Card>
                <CardHeader>
                  <CardTitle>Call Details</CardTitle>
                  <CardDescription>
                    Enter phone number to initiate call
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div>
                    <label
                      htmlFor="phone"
                      className="block text-sm font-medium text-gray-700 mb-2"
                    >
                      Phone Number
                    </label>
                    <input
                      type="tel"
                      id="phone"
                      value={phoneNumber || ''}
                      onChange={(e) =>
                        setPhoneNumber(e.target.value as E164Number)
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Enter phone number"
                    />
                  </div>

                  <Button
                    type="submit"
                    disabled={!phoneNumber || createCallMutation.isPending}
                    className="w-full"
                  >
                    {createCallMutation.isPending
                      ? 'Starting Call...'
                      : 'Start Voice AI Call'}
                  </Button>
                </CardContent>
              </Card>
            </div>
          )}
        </form>

        {/* Success Message */}
        {createCallMutation.isSuccess && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-green-800 text-sm">
              ✅ Voice AI call started successfully! Call ID:{' '}
              {createCallMutation.data?.call_id}
            </p>
          </div>
        )}

        {/* Error Message */}
        {createCallMutation.isError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 text-sm">
              ❌ Failed to start call:{' '}
              {createCallMutation.error?.message || 'Unknown error'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
