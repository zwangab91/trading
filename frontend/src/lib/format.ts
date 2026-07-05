export function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(value);
}

export function formatPrice(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2
  }).format(value);
}

export function formatPercent(value: number, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatSignedPercent(value: number, digits = 1) {
  const formatted = formatPercent(value, digits);
  return value > 0 ? `+${formatted}` : formatted;
}

export function formatNumber(value: number, digits = 2) {
  return value.toFixed(digits);
}

export function compactDate(value: string) {
  return value.slice(0, 10);
}
