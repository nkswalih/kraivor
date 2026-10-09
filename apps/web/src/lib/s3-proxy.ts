const S3_BASE = 'https://kraivor-uploads.s3.amazonaws.com';
const PROXY_PREFIX = '/s3-proxy';

export function s3ProxyUrl(url: string): string {
  if (url.startsWith(S3_BASE)) {
    return url.replace(S3_BASE, PROXY_PREFIX);
  }
  return url;
}
