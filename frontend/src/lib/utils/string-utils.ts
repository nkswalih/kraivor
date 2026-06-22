export const maskEmail = (email: string) => {
  const [localPart, domain] = email.split('@');
  if (!localPart || !domain) return email;
  const maskedLocal = localPart.substring(0, 2) + '*'.repeat(5);
  return `${maskedLocal}@${domain}`;
};
