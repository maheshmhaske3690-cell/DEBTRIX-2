"use client";

import { useEffect, useState } from "react";

interface MetricCardProps {
  label: string;
  value: number;
  format: "score" | "currency" | "hours" | "days";
  currency?: string;
  accent?: "gold" | "health" | "loss";
}

function formatValue(value: number, format: MetricCardProps["format"], currency: string) {
  switch (format) {
    case "score":
      return value.toFixed(0);
    case "currency":
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
        maximumFractionDigits: 0,
      }).format(value);
    case "hours":
      return `${value.toFixed(0)} hrs`;
    case "days":
      return `${value.toFixed(1)} days`;
  }
}

/**
 * Signature element: the number counts up on mount rather than
 * appearing instantly — a small "ledger tallying up" moment that
 * reinforces these are computed, auditable figures, not decoration.
 * Respects prefers-reduced-motion via the CSS layer in globals.css.
 */
export function MetricCard({ label, value, format, currency = "USD", accent = "gold" }: MetricCardProps) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const duration = 700;
    const start = performance.now();
    let frame: number;

    function tick(now: number) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(value * eased);
      if (progress < 1) frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value]);

  const accentClass = {
    gold: "text-gold",
    health: "text-health",
    loss: "text-loss",
  }[accent];

  return (
    <div className="relative overflow-hidden rounded-lg border border-ink-700 bg-ink-900 p-5 sm:p-6">
      <p className="text-xs uppercase tracking-wider text-muted font-body font-medium">{label}</p>
      <p className={`mt-2 font-mono text-3xl sm:text-4xl font-medium tabular ${accentClass}`}>
        {formatValue(display, format, currency)}
      </p>
      {/* the "leak" motif — a thin depleting bar under loss-oriented cards */}
      {accent === "loss" && (
        <div className="mt-4 h-[2px] w-full bg-ink-800 overflow-hidden rounded-full">
          <div className="h-full bg-loss/70 animate-pulse" style={{ width: "70%" }} />
        </div>
      )}
    </div>
  );
}
