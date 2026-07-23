'use client';

import { pdfjs, Document, Page } from 'react-pdf';
import type { PdfElementData } from '@/types/knowledge';
import { s3ProxyUrl } from '@/lib/s3-proxy';

pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';

interface Props {
  data: PdfElementData;
}

export function PdfElement({ data }: Props) {
  if (!data.url) {
    return (
      <div className="w-full h-full bg-krait-surface3 flex items-center justify-center overflow-hidden">
        <div className="flex flex-col items-center gap-2 text-text-tertiary">
          <svg
            className="w-8 h-8"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
            />
          </svg>
          <span className="text-[12px]">PDF not available</span>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex items-center justify-center overflow-hidden bg-white rounded-lg">
      <Document
        file={s3ProxyUrl(data.url)}
        className="flex flex-col items-center"
        loading={
          <div className="flex items-center justify-center w-full h-full text-text-tertiary text-[12px]">
            Loading page {data.pageNumber}...
          </div>
        }
        error={
          <div className="flex items-center justify-center w-full h-full text-red-400 text-[12px]">
            Failed to load page {data.pageNumber}
          </div>
        }
      >
        <Page
          pageNumber={data.pageNumber}
          scale={data.scale}
          className="pdf-page"
          renderTextLayer={false}
          renderAnnotationLayer={false}
        />
      </Document>
    </div>
  );
}
