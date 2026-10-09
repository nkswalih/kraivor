/**
 * Format one engine's result count for the small slots an engine row has.
 *
 * The count appears in the same 56px ring and the same narrow sidebar row as
 * a 0-100 score, so it has room for about four characters. Counts under
 * 10,000 are shown exactly -- that is the range a reader compares at a glance
 * ("9,914 dead-code entries" is the number they will quote). Larger counts are
 * abbreviated the way a dashboard abbreviates a large figure, because a
 * seven-digit number would overflow the ring rather than inform.
 *
 * The locale is pinned to en-US so the same run renders the same string on
 * every machine, which is also what lets the tests assert on it.
 */
export function formatEngineCount(count: number): string {
  if (count < 10_000) return count.toLocaleString('en-US');
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(count);
}
