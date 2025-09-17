import { Trash2 } from 'lucide-react';
import { useRef } from 'react';

import { Button } from '@/components/ui/button';

interface FileSelectorProps {
  file: File | null;
  accept: string;
  disabled?: boolean;
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onClearFile: () => void;
  label?: string;
  placeholder?: string;
}

export function FileSelector({
  file,
  accept,
  disabled = false,
  onFileChange,
  onClearFile,
  label,
  placeholder = 'No file chosen',
}: FileSelectorProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleChooseFile = () => {
    fileInputRef.current?.click();
  };

  return (
    <div>
      {label && (
        <label className="block text-sm font-semibold text-primary-800 mb-3">
          {label}
        </label>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        onChange={onFileChange}
        disabled={disabled}
        className="hidden"
      />

      {!file ? (
        /* Show Choose File button when no file selected */
        <Button
          onClick={handleChooseFile}
          variant="secondary"
          disabled={disabled}
          className="w-full"
          size="lg"
        >
          Choose File
        </Button>
      ) : (
        /* Show selected file with trash icon */
        <div className="p-4 bg-white border-2 border-primary-400 rounded-lg">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0 flex-1">
              <p className="text-sm text-primary-900 font-medium">
                <span className="font-bold truncate block" title={file.name}>
                  {file.name}
                </span>
              </p>
              <p className="text-xs text-primary-600 mt-1">
                Size: {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            <Button
              onClick={onClearFile}
              variant="ghost"
              size="sm"
              disabled={disabled}
              className="text-red-600 hover:text-red-700 hover:bg-red-50 shrink-0"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {!file && (
        <p className="text-sm text-primary-600 mt-2 text-center">
          {placeholder}
        </p>
      )}
    </div>
  );
}
