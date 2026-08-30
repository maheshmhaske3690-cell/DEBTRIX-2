import { api } from "@/lib/api";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-ink-950 flex items-center justify-center px-4">
      <div className="text-center max-w-sm">
        <h1 className="font-display text-3xl font-bold text-paper">Debtrix</h1>
        <p className="mt-2 text-sm text-muted font-body">
          See what your technical debt is actually costing you, every month.
        </p>
        <a
          href={api.githubLoginUrl()}
          className="mt-8 inline-block w-full rounded-md bg-gold px-5 py-3 text-sm font-body font-semibold text-ink-950 hover:bg-gold-soft transition-colors"
        >
          Continue with GitHub
        </a>
      </div>
    </main>
  );
}
