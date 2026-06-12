'use client';

import { useEffect } from 'react';
import { useSearchParams } from 'next/navigation';

export default function OAuthSuccessPage() {
  const searchParams = useSearchParams();

  useEffect(() => {
    const isGitHubAppInstalled = searchParams.get('github_app_installed') === '1';
    const isGitHubAppError = searchParams.get('github_app_install_error') === '1';
    const installationId = searchParams.get('installation_id');
    const workspaceId = searchParams.get('workspace_id');
    const noState = searchParams.get('no_state') === '1';

    if (isGitHubAppInstalled || isGitHubAppError) {
      const isPopup = Boolean(window.opener && window.opener !== window);

      if (isPopup) {
        window.opener.postMessage(
          {
            type: isGitHubAppInstalled ? 'github-app-installed' : 'github-app-install-error',
            installationId: installationId ? parseInt(installationId, 10) : null,
            workspaceId: workspaceId ?? null,
            noState,
            error: isGitHubAppError ? searchParams.get('detail') : null,
          },
          window.location.origin,
        );
        window.close();
        return;
      }

      if (workspaceId) {
        window.location.href = `/${workspaceId}/repositories`;
      } else {
        window.location.href = '/';
      }
      return;
    }

    // Keep existing OAuth login/signup flow below (unchanged)
  }, [searchParams]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-sm text-muted-foreground">Completing authorization...</p>
    </div>
  );
}
