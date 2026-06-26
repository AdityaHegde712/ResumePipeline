/**
 * Format an ISO date string into a human-readable form.
 * Example: "2026-06-25T14:30:00Z" → "Jun 25, 2026"
 */
export function formatDate(iso: string): string {
  const date = new Date(iso);
  if (isNaN(date.getTime())) return iso;

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}
