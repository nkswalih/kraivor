// Ambient fallbacks for packages whose published types do not resolve under
// this project's `moduleResolution: "bundler"`.
//
// The `react-markdown` shim that used to live here was deleted, and that was the
// single change that made `import type { Components } from 'react-markdown'`
// resolve. An ambient `declare module 'react-markdown'` *replaces* the package's
// own types rather than augmenting them, so the real `Components` type was
// invisible and every element override had to be typed `any`. Keeping a shim
// for a package that ships types silently discards them -- check
// `node_modules/<pkg>/package.json` for a `types` field before adding one.

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
