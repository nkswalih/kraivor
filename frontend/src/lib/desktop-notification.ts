/**
 * Browser desktop notification helper.
 * Requests permission and sends desktop notifications.
 */

export function isDesktopNotificationSupported(): boolean {
  return 'Notification' in window;
}

export function hasDesktopNotificationPermission(): boolean {
  return isDesktopNotificationSupported() && Notification.permission === 'granted';
}

export async function requestDesktopNotificationPermission(): Promise<boolean> {
  if (!isDesktopNotificationSupported()) return false;
  if (Notification.permission === 'granted') return true;
  if (Notification.permission === 'denied') return false;

  const permission = await Notification.requestPermission();
  return permission === 'granted';
}

export function sendDesktopNotification(
  title: string,
  options?: {
    body?: string;
    icon?: string;
    tag?: string;
    onClick?: () => void;
  },
): void {
  if (!hasDesktopNotificationPermission()) return;

  try {
    const notif = new Notification(title, {
      body: options?.body,
      icon: options?.icon ?? '/favicon.ico',
      tag: options?.tag,
    });

    if (options?.onClick) {
      notif.onclick = () => {
        window.focus();
        options.onClick!();
        notif.close();
      };
    }

    setTimeout(() => notif.close(), 5000);
  } catch {
    // Desktop notification not available
  }
}
