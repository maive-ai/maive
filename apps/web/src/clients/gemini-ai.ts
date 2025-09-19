import {
  AIApi,
  Configuration,
  JobStatus,
  type JobStartResponse,
  type JobStatusResponse,
  type QueryRequest,
} from '@maive/api-serverless/client';

import { getIdToken } from '@/auth';
import { env } from '@/env';

export async function createAiClient() {
  const token = await getIdToken();
  if (!token) throw new Error('Not authenticated');
  return new AIApi(
    new Configuration({
      accessToken: token,
      basePath: env.PUBLIC_SERVER_URL,
    }),
  );
}

export interface AiJobResult {
  success: boolean;
  message: string;
  jobId?: string;
  status?: JobStatus;
  response?: string;
  csvOutput?: string;
  thoughts?: string;
  lowConfidenceCells?: Array<[number, number]>;
  error?: Error;
}

export async function startAiJob(
  s3Key: string,
  prompt: string,
  workflowId?: string,
): Promise<AiJobResult> {
  try {
    const aiClient = await createAiClient();

    const queryRequest: QueryRequest = {
      s3_key: s3Key,
      prompt: prompt,
      ...(workflowId && { workflow_id: workflowId }),
    };

    const response = await aiClient.startAiJob(queryRequest);
    const data = response.data as JobStartResponse;

    return {
      success: true,
      message: data.message,
      jobId: data.job_id,
      status: data.status,
    };
  } catch (error) {
    console.error('AI job start error:', error);
    return {
      success: false,
      message: 'Oops! Failed to start AI processing. Please try again.',
      error:
        error instanceof Error
          ? error
          : new Error('Unknown AI job start error'),
    };
  }
}

export async function getAiJobStatus(jobId: string): Promise<AiJobResult> {
  try {
    const aiClient = await createAiClient();
    const response = await aiClient.getAiJobStatus(jobId);
    const data = response.data as JobStatusResponse;

    const result: AiJobResult = {
      success: true,
      message: data.message,
      jobId: data.job_id,
      status: data.status,
    };

    // If job is completed, include the AI response
    if (data.status === JobStatus.Completed && data.result) {
      const geminiResponse = data.result.gemini_response;

      // Extract text content (may be null in Step Functions responses to reduce size)
      if (geminiResponse.text_content) {
        result.response = geminiResponse.text_content;
      }

      // Extract thoughts
      result.thoughts = geminiResponse.thoughts;

      // Extract CSV output
      result.csvOutput = data.result.csv_output;

      // Extract low confidence cells
      if (data.result.low_confidence_cells) {
        result.lowConfidenceCells = data.result.low_confidence_cells as Array<
          [number, number]
        >;
      }
    }

    // If job failed, include error
    if (data.status === JobStatus.Failed && data.error) {
      result.error = new Error(data.error);
    }

    return result;
  } catch (error) {
    console.error('AI job status error:', error);
    return {
      success: false,
      message: 'Oops! Failed to check job status. Please try again.',
      error:
        error instanceof Error ? error : new Error('Unknown job status error'),
    };
  }
}

// Helper function to poll for job completion
export async function pollForJobCompletion(
  jobId: string,
  onUpdate?: (result: AiJobResult) => void,
  maxAttempts: number = 120, // 10 minutes with 5-second intervals
  intervalMs: number = 5000,
): Promise<AiJobResult> {
  let attempts = 0;

  while (attempts < maxAttempts) {
    const result = await getAiJobStatus(jobId);

    if (onUpdate) {
      onUpdate(result);
    }

    if (!result.success) {
      return result;
    }

    if (
      result.status === JobStatus.Completed ||
      result.status === JobStatus.Failed
    ) {
      return result;
    }

    // Wait before next poll
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
    attempts++;
  }

  return {
    success: false,
    message:
      'AI processing is taking longer than expected. Please check back later.',
    error: new Error('Job polling timeout'),
  };
}
