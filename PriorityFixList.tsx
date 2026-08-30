import type { PriorityFix } from "@/lib/api";

interface Props {
  fixes: PriorityFix[];
  currency: string;
}

export function PriorityFixList({ fixes, currency }: Props) {
  if (fixes.length === 0) {
    return (
      <div className="rounded-lg border border-ink-700 bg-ink-900 p-6 text-muted text-sm">
        No high-impact files detected in the latest scan.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-ink-700 bg-ink-900 divide-y divide-ink-800">
      {fixes.map((fix) => (
        <div key={fix.file_path} className="flex items-start gap-4 p-5 sm:p-6">
          <span className="font-mono text-xl text-gold/80 font-medium leading-none mt-1">
            {String(fix.rank).padStart(2, "0")}
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-mono text-sm text-paper truncate">{fix.file_path}</p>
            <p className="mt-1 text-sm text-muted font-body">{fix.reason_summary}</p>
          </div>
          <p className="font-mono text-sm sm:text-base text-loss whitespace-nowrap tabular">
            {new Intl.NumberFormat("en-US", {
              style: "currency",
              currency,
              maximumFractionDigits: 0,
            }).format(fix.estimated_monthly_loss)}
            <span className="text-muted text-xs">/mo</span>
          </p>
        </div>
      ))}
    </div>
  );
}
