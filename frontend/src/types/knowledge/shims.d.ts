declare module 'react-markdown' {
  import type { ComponentType, ReactNode } from 'react';
  interface ReactMarkdownProps {
    children?: string;
    className?: string;
        components?: Record<string, ComponentType<any>>;
    [key: string]: unknown;
  }
  const ReactMarkdown: ComponentType<ReactMarkdownProps>;
  export default ReactMarkdown;
}

declare module '@monaco-editor/react' {
  import type { ComponentType } from 'react';
  interface EditorProps {
    defaultLanguage?: string;
    defaultValue?: string;
    language?: string;
    value?: string;
    theme?: string;
    options?: Record<string, unknown>;
    onChange?: (value: string | undefined) => void;
    height?: string | number;
    className?: string;
    [key: string]: unknown;
  }
  export const Editor: ComponentType<EditorProps>;
  export const DiffEditor: ComponentType<Record<string, unknown>>;
  export const useMonaco: () => unknown;
  export const loader: { init: () => Promise<unknown> };
}

declare module 'react-pdf' {
  import type { ComponentType } from 'react';
  interface DocumentProps {
    file: string | { url: string };
    onLoadSuccess?: (pdf: { numPages: number }) => void;
    className?: string;
    [key: string]: unknown;
  }
  interface PageProps {
    pageNumber: number;
    width?: number;
    height?: number;
    scale?: number;
    className?: string;
    [key: string]: unknown;
  }
  export const Document: ComponentType<DocumentProps>;
  export const Page: ComponentType<PageProps>;
  export { pdfjs } from 'react-pdf';
}
