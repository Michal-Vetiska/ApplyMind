import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value?: string | null, withTime = false): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("cs-CZ", {
    dateStyle: "medium",
    ...(withTime ? { timeStyle: "short" } : {}),
  }).format(date);
}

export function formatSalary(
  min?: number | null,
  max?: number | null,
  currency = "CZK",
  flag?: string | null,
): string {
  if (flag === "SALARY_UNKNOWN" || (min == null && max == null)) {
    return "Neuvedeno";
  }
  const fmt = (n: number) =>
    new Intl.NumberFormat("cs-CZ", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(n);
  if (min != null && max != null) return `${fmt(min)} – ${fmt(max)}`;
  if (min != null) return `od ${fmt(min)}`;
  if (max != null) return `do ${fmt(max)}`;
  return "Neuvedeno";
}

export function formatPercent(value?: number | null, digits = 0): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${value.toFixed(digits)} %`;
}

export function formatScore(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  return Math.round(value).toString();
}

export function buildQuery(params: Record<string, string | number | boolean | undefined | null>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}
