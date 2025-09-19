import { BarChart3, Brain, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

import { Button } from '@/components/ui/button';

interface OutputResultsProps {
  excelOutput: File | null;
  aiThoughts: string | null;
}

export function OutputResults({ excelOutput, aiThoughts }: OutputResultsProps) {
  const handleDownload = () => {
    if (!excelOutput) return;

    const blob = new Blob([excelOutput], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = excelOutput.name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!excelOutput) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Excel Output */}
      {excelOutput && (
        <div className="bg-primary-50 rounded-xl shadow-sm border-2 border-primary-600 p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <BarChart3 className="w-6 h-6 text-primary-700" />
              <h3 className="text-xl font-bold text-primary-900">
                Excel Output
              </h3>
            </div>
            <Button
              onClick={handleDownload}
              size="sm"
              className="bg-secondary-500 hover:bg-secondary-600 text-primary-900"
            >
              <Download className="w-4 h-4" />
              Download
            </Button>
          </div>
          <div className="bg-secondary-50 border-2 border-secondary-200 rounded-lg p-4">
            <div className="text-sm text-secondary-800 font-mono overflow-x-auto">
              <pre className="whitespace-pre-wrap">{excelOutput.name}</pre>
            </div>
          </div>
        </div>
      )}

      {/* AI Thoughts */}
      {aiThoughts && (
        <div className="lg:col-span-2 bg-primary-50 rounded-xl shadow-sm border-2 border-primary-600 p-8">
          <details className="group">
            <summary className="cursor-pointer flex items-center gap-3 mb-4 list-none [&::-webkit-details-marker]:hidden">
              <Brain className="w-6 h-6 text-primary-700" />
              <h3 className="text-xl font-bold text-primary-900">
                AI Thoughts
              </h3>
              <div className="ml-auto text-primary-600 group-open:rotate-180 transition-transform">
                ▼
              </div>
            </summary>
            <div className="bg-neutral-100 border-2 border-neutral-200 rounded-lg p-4 max-h-96 overflow-y-auto">
              <div className="prose prose-sm text-primary-800 max-w-none">
                <ReactMarkdown>{aiThoughts}</ReactMarkdown>
              </div>
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
