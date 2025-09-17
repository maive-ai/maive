import { JobStatus } from '@maive/api-serverless/client';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Pen, Play } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import type { WorkBook } from 'xlsx';

import { FileUpload } from '../nodes/FileUpload';
import { OutputResults } from '../nodes/OutputResults';
import { OutputTemplate } from '../nodes/OutputTemplate';
import { TransformConfiguration } from '../nodes/TransformConfiguration';

import { useAuth } from '@/auth';
import {
  pollForJobCompletion,
  startAiJob,
  type AiJobResult,
} from '@/clients/gemini-ai';
import { processTemplate } from '@/clients/templates';
import { uploadFile, type UploadProgress } from '@/clients/upload';
import { fetchWorkflow, updateWorkflow } from '@/clients/workflows';
import Loading from '@/components/Loading';
import { Button } from '@/components/ui/button';
import { csvToFile, getHeadersFromWorkbook, parseWorkbook } from '@/lib/excel';
import { useAutoSave } from '@/lib/utils';

interface StructuredGenerationProps {
  workflowId: string; // Always defined since workflows are created immediately
}

export function StructuredGeneration({
  workflowId,
}: StructuredGenerationProps) {
  const auth = useAuth();
  const queryClient = useQueryClient();

  // Fetch workflow data
  const {
    data: workflow,
    isLoading: isLoadingWorkflow,
    error,
  } = useQuery({
    queryKey: ['workflow', workflowId],
    queryFn: () => fetchWorkflow(workflowId),
    enabled: auth.isAuthenticated,
  });

  // Workflow state
  const [workflowName, setWorkflowName] = useState('');
  const [prompt, setPrompt] = useState('');

  // File upload state
  const [uploadedKey, setUploadedKey] = useState<string | undefined>(undefined);
  const [fileUploading, setFileUploading] = useState(false);

  // AI processing state
  const [querying, setQuerying] = useState(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [, setCsvOutput] = useState<string | null>(null);
  const [excelOutput, setExcelOutput] = useState<File | null>(null);
  const [aiThoughts, setAiThoughts] = useState<string | null>(null);

  // Template upload state
  const [template, setTemplate] = useState<{
    file: File;
    workbook: WorkBook;
    name: string;
  } | null>(null);
  const [templateUploading, setTemplateUploading] = useState(false);
  const [templateUploadProgress, setTemplateUploadProgress] = useState(0);
  const [templateMessage, setTemplateMessage] = useState('');

  const [templateUploaded, setTemplateUploaded] = useState(false);
  const [showRunTooltip, setShowRunTooltip] = useState(false);

  // Load workflow data into local state when it's fetched
  useEffect(() => {
    if (workflow) {
      setWorkflowName(workflow.name);
      setPrompt(workflow.prompt);

      // Load existing template data if available
      if (workflow.template) {
        setTemplateMessage(`Template loaded: ${workflow.template.filename}`);
        setTemplateUploaded(true);
      }
    }
  }, [workflow]);

  // Memoized save function to prevent recreation on every render
  const saveFunction = useCallback(
    async (data: { name: string; prompt: string }) => {
      if (!data.name.trim() || !data.prompt.trim()) {
        return;
      }
      return await updateWorkflow(workflowId, {
        name: data.name.trim(),
        prompt: data.prompt.trim(),
      });
    },
    [workflowId],
  );

  // Auto-save hook for workflow data (runs in background)
  void useAutoSave({ name: workflowName, prompt }, saveFunction, {
    debounceMs: 1000, // 1 second debounce
    enabled:
      !!workflow &&
      (workflowName.trim() !== workflow.name ||
        prompt.trim() !== workflow.prompt),
    onSuccess: () => {
      console.log('✅ Workflow auto-saved successfully');
      // Only invalidate the workflows list to reflect changes
      // Don't update the current workflow cache to avoid overwriting user input
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
    onError: (error) => {
      console.error('❌ Workflow auto-save failed:', error);
    },
  });

  const handleTemplateProgress = (progress: UploadProgress) => {
    setTemplateUploadProgress(progress.percentage);
  };

  const handleTemplateFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const selectedFile = event.target.files?.[0];
    setTemplateMessage('');
    if (!selectedFile) {
      setTemplate(null);
      return;
    }
    try {
      const acceptedTypes = [
        'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      ];
      if (acceptedTypes.includes(selectedFile.type)) {
        const workbook = await parseWorkbook(selectedFile);
        setTemplate({
          file: selectedFile,
          workbook: workbook,
          name: selectedFile.name,
        });
      } else {
        setTemplate(null);
        setTemplateMessage(
          'Please select a CSV or Excel file. Templates must be in CSV or Excel format! 📊',
        );
      }
    } catch (error) {
      console.error('Error setting template:', error);
      setTemplate(null);
      setTemplateMessage(
        'Oops! Something went wrong setting the template. Please check your file and try again.',
      );
    }
  };

  const handleTemplateClear = () => {
    setTemplate(null);
    setTemplateMessage('');
  };

  // Now accepts header selection: isHeaderRow, headerValue
  const handleTemplateUpload = async (
    isHeaderRow: boolean,
    headerValue: string,
    selectedSheet?: string,
  ) => {
    if (!template || !auth.isAuthenticated) return;

    setTemplateUploading(true);
    setTemplateUploadProgress(0);
    setTemplateMessage('');

    try {
      // Build header file based on user's selection
      const headers = await getHeadersFromWorkbook(
        template.workbook,
        isHeaderRow,
        headerValue,
        selectedSheet,
      );
      // Create a CSV file with the headers
      const headerCsv = headers.join(',');
      const headerFile = new File(
        [headerCsv],
        template.name.replace(/\.[^.]+$/, '.csv'),
        { type: 'text/csv' },
      );
      // Upload the header file
      const result = await uploadFile(headerFile, {
        onProgress: handleTemplateProgress,
      });

      if (result.success) {
        setTemplateMessage(result.message);

        // Process the template after successful upload
        if (auth.user?.email) {
          setTemplateMessage('Processing template...');
          const processResult = await processTemplate(
            result.key!,
            auth.user.email,
            workflowId,
          );

          if (processResult.success) {
            setTemplateMessage(
              `${result.message} Template processed successfully!`,
            );
            setTemplateUploaded(true);
          } else {
            setTemplateMessage(
              `${result.message} Warning: Template uploaded but processing failed: ${processResult.message}`,
            );
            setTemplateUploaded(false);
          }
        } else {
          setTemplateMessage(
            `${result.message} Warning: Template uploaded but cannot be processed (missing user email)`,
          );
          setTemplateUploaded(false);
        }
      }
    } catch (error) {
      console.error('Template upload error:', error);
      setTemplateMessage(
        'Oops! Something went wrong with your template upload. Please try again.',
      );
      setTemplateUploaded(false);
    } finally {
      setTemplateUploading(false);
      setTemplateUploadProgress(0);
    }
  };

  const handleAiQuery = async () => {
    if (!uploadedKey || !prompt.trim() || !auth.isAuthenticated) return;

    setQuerying(true);
    setCsvOutput(null);
    setExcelOutput(null);
    setAiThoughts(null);
    setCurrentJobId(null);
    setJobStatus(null);

    try {
      const startResult = await startAiJob(uploadedKey, prompt, workflowId);

      if (!startResult.success || !startResult.jobId) {
        setQuerying(false);
        return;
      }

      setCurrentJobId(startResult.jobId);
      setJobStatus(startResult.status || JobStatus.Started);

      const finalResult = await pollForJobCompletion(
        startResult.jobId,
        (updateResult: AiJobResult) => {
          setJobStatus(updateResult.status || null);
        },
      );

      if (finalResult.success && finalResult.status === JobStatus.Completed) {
        setCsvOutput(finalResult.csvOutput || null);
        setAiThoughts(finalResult.thoughts || null);
        // Log uncertain cells for debugging
        if (
          finalResult.lowConfidenceCells &&
          finalResult.lowConfidenceCells.length > 0
        ) {
          console.log(
            `Found ${finalResult.lowConfidenceCells.length} uncertain cells for highlighting`,
          );
        }
        const outputFileName = `${workflowName}_${new Date().toISOString().split('T')[0]}`;
        const excelOutput = csvToFile(
          finalResult.csvOutput || '',
          outputFileName,
          finalResult.lowConfidenceCells,
        );
        setExcelOutput(excelOutput);
        setJobStatus(JobStatus.Completed);
      } else {
        setJobStatus(finalResult.status || JobStatus.Failed);
        if (finalResult.error) {
          console.error('AI processing error:', finalResult.error);
        }
      }
    } catch (error) {
      console.error('AI query error:', error);
      setJobStatus(JobStatus.Failed);
    } finally {
      setQuerying(false);
    }
  };

  // Loading state
  if (isLoadingWorkflow) {
    return <Loading />;
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-neutral-50">
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-6" />
            <h3 className="text-xl font-semibold text-primary-900 mb-3">
              Failed to load workflow
            </h3>
            <p className="text-primary-600 mb-6 max-w-md">
              The workflow could not be found or there was an error loading it.
            </p>
            <Button onClick={() => window.history.back()}>Go Back</Button>
          </div>
        </div>
      </div>
    );
  }

  const getRunButtonTooltip = () => {
    if (!prompt.trim()) return 'Prompt is required to run AI';
    if (!templateUploaded) return 'Template is required to run AI';
    if (fileUploading) return 'Please wait for file upload to complete';
    return '';
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Top Header - Workflow Name and Save Button */}
      <div className="bg-primary-50">
        <div className="max-w-7xl mx-auto px-8 py-8">
          <div className="flex items-start justify-between gap-8">
            <div className="flex-1">
              <div className="relative inline-block">
                <input
                  type="text"
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  className="text-3xl font-bold bg-transparent border-none outline-none focus:bg-neutral-100 focus:shadow-sm focus:rounded-lg px-3 py-2 pr-16 text-primary-900 placeholder-primary-500"
                  placeholder="Workflow Name"
                  style={{
                    width: `${Math.max(
                      (workflowName || 'Workflow Name').length + 3,
                      12,
                    )}ch`,
                    maxWidth: '32rem',
                    minWidth: '12ch',
                  }}
                />
                <Pen className="absolute right-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-primary-500 pointer-events-none" />
              </div>
            </div>

            <div className="shrink-0 flex items-center gap-4">
              {/* AI Analysis Controls */}
              {uploadedKey && (
                <div
                  className="relative inline-block"
                  onMouseEnter={() => setShowRunTooltip(true)}
                  onMouseLeave={() => setShowRunTooltip(false)}
                >
                  <Button
                    onClick={handleAiQuery}
                    disabled={
                      !prompt.trim() ||
                      querying ||
                      !templateUploaded ||
                      fileUploading
                    }
                    className="bg-accent-500 hover:bg-accent-600 text-primary-900 min-w-[180px]"
                    size="lg"
                    title={getRunButtonTooltip()}
                  >
                    <Play className="w-4 h-4" />
                    {querying
                      ? jobStatus === JobStatus.Started
                        ? 'Starting AI processing...'
                        : jobStatus === JobStatus.Processing
                          ? 'AI is thinking...'
                          : 'Processing...'
                      : 'Run'}
                  </Button>
                  {showRunTooltip &&
                    (!prompt.trim() || !templateUploaded || fileUploading) && (
                      <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 px-2 py-1 bg-gray-800 text-white text-xs rounded whitespace-nowrap z-10">
                        {getRunButtonTooltip()}
                      </div>
                    )}
                </div>
              )}

              {/* Job Status Display */}
              {currentJobId && (
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary-50 border-2 border-primary-200 h-10">
                  <span className="text-sm font-medium text-primary-900">
                    Status:
                  </span>
                  <span
                    className={`text-xs px-2 py-1 rounded-full font-medium ${
                      jobStatus === JobStatus.Completed
                        ? 'bg-green-100 text-green-800 border border-green-200'
                        : jobStatus === JobStatus.Failed
                          ? 'bg-red-100 text-red-800 border border-red-200'
                          : jobStatus === JobStatus.Processing
                            ? 'bg-yellow-100 text-yellow-800 border border-yellow-200'
                            : 'bg-secondary-100 text-secondary-800 border border-secondary-200'
                    }`}
                  >
                    {jobStatus || 'UNKNOWN'}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="max-w-7xl mx-auto px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Left Column - Input Section (1/4 width) */}
          <div className="space-y-6">
            <FileUpload
              onUploadSuccess={(key: string) => {
                setUploadedKey(key === '' ? undefined : key);
                setCsvOutput(null);
                setExcelOutput(null);
                setAiThoughts(null);
                setCurrentJobId(null);
                setJobStatus(null);
              }}
              onUploadStateChange={setFileUploading}
            />
          </div>

          {/* Middle Column - Transform Section (2/4 width) */}
          <div className="lg:col-span-2 space-y-6">
            <TransformConfiguration
              prompt={prompt}
              onPromptChange={setPrompt}
            />
          </div>

          {/* Right Column - Output Template Section (1/4 width) */}
          <div className="space-y-6">
            <OutputTemplate
              template={template}
              templateUploading={templateUploading}
              templateUploadProgress={templateUploadProgress}
              templateMessage={templateMessage}
              workflow={workflow}
              onTemplateFileChange={handleTemplateFileChange}
              onTemplateClear={handleTemplateClear}
              onTemplateUpload={handleTemplateUpload}
            />
          </div>
        </div>

        {/* Results Section */}
        {excelOutput && (
          <div className="mt-12">
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-primary-900">Results</h2>
            </div>
            <OutputResults excelOutput={excelOutput} aiThoughts={aiThoughts} />
          </div>
        )}
      </div>
    </div>
  );
}
