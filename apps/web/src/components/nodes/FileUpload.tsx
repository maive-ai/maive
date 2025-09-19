import { FileText, Image } from 'lucide-react';
import { useState } from 'react';

import { useAuth } from '@/auth';
import { Input } from '@/components/ui/input';
// import { uploadFile, type UploadProgress } from '@/clients/upload';

// Placeholder types and functions
type UploadProgress = {
  percentage: number;
};

const uploadFile = async (file: File, options?: { onProgress?: (progress: UploadProgress) => void }): Promise<{ success: boolean; message: string; key?: string }> => {
  // Simulate upload progress
  if (options?.onProgress) {
    for (let i = 0; i <= 100; i += 10) {
      setTimeout(() => options.onProgress!({ percentage: i }), i * 10);
    }
  }
  
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        success: true,
        message: 'File uploaded successfully (placeholder)',
        key: `placeholder-${Date.now()}`,
      });
    }, 1000);
  });
};

type FileType = 'pdf' | 'image';

interface FileUploadProps {
  onUploadSuccess: (key: string) => void;
  onUploadStateChange?: (uploading: boolean) => void;
}

export function FileUpload({
  onUploadSuccess,
  onUploadStateChange,
}: FileUploadProps) {
  const auth = useAuth();

  const [fileType, setFileType] = useState<FileType | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [message, setMessage] = useState('');

  const handleProgress = (progress: UploadProgress) => {
    setUploadProgress(progress.percentage);
  };

  const handleFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) {
      setFileType(null);
      return;
    }

    // Check for PDF files
    if (selectedFile.type === 'application/pdf') {
      setFileType('pdf');
      setMessage('');
      // Auto-upload PDF files
      await handleUpload(selectedFile);
      return;
    }

    // Check for supported image formats (as per Gemini API docs)
    const supportedImageTypes = ['image/png', 'image/jpeg', 'image/heic'];

    if (supportedImageTypes.includes(selectedFile.type)) {
      setFileType('image');
      setMessage('');
      // Auto-upload image files
      await handleUpload(selectedFile);
      return;
    }

    // Unsupported file type
    setMessage(
      'Please select a PDF or supported image file (PNG, JPEG, HEIC).',
    );
    setFileType(null);
  };

  const handleUpload = async (fileToUpload: File) => {
    if (!auth.isAuthenticated) return;

    setUploading(true);
    onUploadStateChange?.(true);
    setUploadProgress(0);
    setMessage('');

    try {
      const result = await uploadFile(fileToUpload, {
        onProgress: handleProgress,
      });

      if (result.success) {
        setMessage(result.message);
        onUploadSuccess(result.key!); // Notify parent of successful upload
      } else {
        setMessage(result.message || 'Upload failed. Please try again.');
      }
    } catch (error) {
      console.error('Upload error:', error);
      setMessage(
        'Oops! Something went wrong with your upload. Please try again.',
      );
    } finally {
      setUploading(false);
      onUploadStateChange?.(false);
      setUploadProgress(0);
    }
  };

  const getFileIcon = () => {
    if (fileType === 'image') {
      return <Image className="w-6 h-6 text-primary-700" />;
    }
    return <FileText className="w-6 h-6 text-primary-700" />;
  };

  const getTitle = () => {
    if (fileType === 'image') {
      return 'Image Input';
    }
    return 'File Upload';
  };

  return (
    <div className="bg-primary-50 rounded-xl shadow-sm border-2 border-primary-900 p-8">
      <div className="flex items-center gap-3 mb-6">
        {getFileIcon()}
        <h2 className="text-xl font-bold text-primary-900">{getTitle()}</h2>
      </div>

      <div className="space-y-6">
        {/* File Input with integrated states */}
        <div className="space-y-3">
          <div className="relative">
            <Input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.heic"
              disabled={uploading}
              onChange={handleFileChange}
              className="file"
            />
          </div>

          {/* Upload Progress */}
          {uploading && (
            <div className="space-y-2">
              <p className="text-sm text-primary-700 text-center font-medium">
                Uploading... {uploadProgress}%
              </p>
              <div className="w-full bg-primary-200 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-accent-500 h-2 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Status Message */}
          {message && (
            <div
              className={`p-3 rounded-lg text-sm font-medium ${
                message.includes('Success')
                  ? 'bg-green-50 border border-green-200 text-green-800'
                  : 'bg-red-50 border border-red-200 text-red-800'
              }`}
            >
              {message}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
