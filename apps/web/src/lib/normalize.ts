export function normalizeList<T>(data: T[] | { items: T[] } | undefined | null): T[] {
  if (!data) return [];
  return Array.isArray(data) ? data : data.items ?? [];
}

export function normalizePaginated<T>(
  data: T[] | { items: T[]; total?: number; limit?: number; offset?: number } | undefined | null,
): { items: T[]; total: number } {
  if (!data) return { items: [], total: 0 };
  if (Array.isArray(data)) return { items: data, total: data.length };
  return { items: data.items ?? [], total: data.total ?? data.items?.length ?? 0 };
}
