import { redirect } from 'next/navigation';

export default function DashboardIndex() {
  // Redirect to the first settings page
  redirect('/dashboard/settings/security');
}
