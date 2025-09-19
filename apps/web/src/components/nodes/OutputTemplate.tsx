import { type Workflow } from '@maive/api/client';
import { Eye, FileSpreadsheet } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import type { WorkBook } from 'xlsx';

import { Button } from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { getHeadersFromWorkbook, getSheetNamesFromWorkbook } from '@/lib/excel';

interface OutputTemplateProps {
  template: { file: File; workbook: WorkBook; name: string } | null;
  templateUploading: boolean;
  templateUploadProgress: number;
  templateMessage: string;
  workflow?: Workflow;
  onTemplateFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onTemplateClear: () => void;
  onTemplateUpload: (
    isHeaderRow: boolean,
    headerValue: string,
    selectedSheet?: string,
  ) => void;
}

export function OutputTemplate({
  template,
  templateUploading,
  templateUploadProgress,
  templateMessage,
  workflow,
  onTemplateFileChange,
  onTemplateClear,
  onTemplateUpload,
}: OutputTemplateProps) {
  const [isHeaderRow, setIsHeaderRow] = useState(true);
  const [headerInputValue, setHeaderInputValue] = useState('');
  const [previewHeaders, setPreviewHeaders] = useState<string[]>([]);
  const [sheetNames, setSheetNames] = useState<string[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<string | undefined>(
    undefined,
  );

  const validateInput = (value: string, isRow: boolean): boolean => {
    if (!value) return true; // Allow empty values

    if (isRow) {
      // For rows: must be a positive integer
      const num = parseInt(value, 10);
      return !isNaN(num) && num > 0 && num.toString() === value;
    } else {
      // For columns: must be valid Excel column letters (A-Z, AA-ZZ, AAA-ZZZ, etc.)
      return /^[A-Za-z]+$/.test(value);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;

    // Allow the change if it's valid or if it's empty (for clearing)
    if (validateInput(value, isHeaderRow)) {
      setHeaderInputValue(isHeaderRow ? value : value.toUpperCase()); // Only uppercase for columns
    }
  };

  // Update preview headers when template, selection mode, or input value changes
  useEffect(() => {
    if (!template) {
      setPreviewHeaders([]);
      return;
    }
    // Async IIFE to fetch and set headers
    (async () => {
      try {
        const headers = await getHeadersFromWorkbook(
          template.workbook,
          isHeaderRow,
          headerInputValue,
          selectedSheet,
        );
        setPreviewHeaders(headers);
      } catch (error) {
        console.error('Error updating preview headers:', error);
        setPreviewHeaders([]);
      }
    })();
  }, [template, isHeaderRow, headerInputValue, selectedSheet]);

  // Effect to load sheet names when a new template file is selected
  useEffect(() => {
    if (template) {
      (async () => {
        try {
          const names = await getSheetNamesFromWorkbook(template.workbook);
          setSheetNames(names);
          if (names.length > 0 && !selectedSheet) {
            setSelectedSheet(names[0]); // Automatically select the first sheet
          }
        } catch (error) {
          console.error('Error loading sheet names:', error);
          setSheetNames([]);
          setSelectedSheet(undefined);
        }
      })();
    } else {
      setSheetNames([]);
      setSelectedSheet(undefined);
    }
  }, [template, selectedSheet]);

  return (
    <div className="bg-primary-50 rounded-xl shadow-sm border-2 border-primary-600 p-8">
      <div className="flex items-center gap-3 mb-8">
        <FileSpreadsheet className="w-6 h-6 text-primary-700" />
        <h2 className="text-xl font-bold text-primary-900">Output Template</h2>
      </div>

      <div className="space-y-6">
        {/* File Input with integrated states */}
        <div className="space-y-3">
          <div className="relative">
            <Input
              type="file"
              accept=".csv,.xls,.xlsx"
              disabled={templateUploading}
              onChange={onTemplateFileChange}
              className="file"
            />
          </div>
        </div>

        {template && (
          <>
            <div className="space-y-4">
              <h3 className="text-md font-semibold text-primary-900">
                Select Header
              </h3>
              <div className="mb-4">
                <Label htmlFor="sheet-select" className="text-sm font-medium">
                  Sheet
                </Label>
                <Select value={selectedSheet} onValueChange={setSelectedSheet}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Select a sheet" />
                  </SelectTrigger>
                  <SelectContent className="bg-white shadow-lg">
                    {sheetNames.map((sheetName) => (
                      <SelectItem key={sheetName} value={sheetName}>
                        {sheetName}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-start gap-4">
                <div className="flex flex-col items-center gap-2">
                  <Switch
                    id="header-toggle"
                    checked={!isHeaderRow}
                    onCheckedChange={(checked) => setIsHeaderRow(!checked)}
                    className="data-[state=checked]:bg-primary-600"
                  />
                  <Label htmlFor="header-toggle" className="text-sm">
                    {isHeaderRow ? 'Row' : 'Column'}
                  </Label>
                </div>
                <Input
                  type={isHeaderRow ? 'number' : 'text'}
                  placeholder={isHeaderRow ? 'Row number' : 'Column letter'}
                  className="max-w-[120px] text-xs placeholder:text-xs"
                  value={headerInputValue}
                  onChange={handleInputChange}
                  min={isHeaderRow ? '1' : undefined}
                />
              </div>
            </div>
            <Dialog>
              <DialogTrigger asChild>
                <button className="flex items-center gap-2 text-primary-600 hover:text-primary-700 transition-colors cursor-pointer">
                  <span className="text-sm">Header Preview:</span>
                  <Eye className="w-4 h-4" />
                </button>
              </DialogTrigger>
              <DialogContent
                className="sm:max-w-4xl bg-primary-50"
                aria-describedby={undefined}
              >
                <DialogHeader>
                  <DialogTitle className="text-primary-900">
                    Header Preview
                  </DialogTitle>
                </DialogHeader>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-secondary-200">
                    <thead className="bg-secondary-50">
                      <tr>
                        {previewHeaders.map((col, index) => (
                          <th
                            key={index}
                            scope="col"
                            className="px-3 py-2 text-left text-xs font-semibold text-secondary-800 uppercase tracking-wider"
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                  </table>
                </div>
              </DialogContent>
            </Dialog>
          </>
        )}

        {templateUploading && (
          <div className="space-y-2">
            <p className="text-sm text-primary-700 text-center font-medium">
              Uploading template... {templateUploadProgress}%
            </p>
            <div className="w-full bg-primary-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-accent-500 h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${templateUploadProgress}%` }}
              />
            </div>
          </div>
        )}

        {templateMessage && (
          <div
            className={`p-4 rounded-lg text-sm font-medium ${
              templateMessage.includes('Processing')
                ? 'bg-orange-50 border-2 border-orange-200 text-orange-800'
                : templateMessage.includes('Success') ||
                    templateMessage.includes('loaded')
                  ? 'bg-green-50 border-2 border-green-200 text-green-800'
                  : 'bg-red-50 border-2 border-red-200 text-red-800'
            }`}
          >
            {templateMessage}
          </div>
        )}

        {template && (
          <Button
            onClick={() =>
              onTemplateUpload(isHeaderRow, headerInputValue, selectedSheet)
            }
            disabled={templateUploading}
            className="w-full"
            size="lg"
          >
            {templateUploading
              ? 'Uploading...'
              : workflow?.template
                ? 'Replace Template'
                : 'Upload Template'}
          </Button>
        )}
      </div>
    </div>
  );
}
