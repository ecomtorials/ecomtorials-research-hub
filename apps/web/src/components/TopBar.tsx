import Link from 'next/link';

export function TopBar({ email }: { email: string | undefined }) {
  return (
    <header className="sticky top-0 z-10 border-b border-[var(--color-border)] bg-[var(--color-bg)]/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-lg font-semibold tracking-tight">Research Hub</span>
          <span className="rounded-full bg-[var(--color-accent-soft)] px-2 py-0.5 text-xs uppercase tracking-wide text-[var(--color-accent)]">
            ecomtorials
          </span>
        </Link>
        <div className="flex items-center gap-3 text-sm text-[var(--color-text-muted)]">
          <span className="hidden sm:inline">{email ?? '—'}</span>
          <form action="/auth/signout" method="post">
            <button className="rounded-md border border-[var(--color-border)] px-3 py-1.5 hover:bg-white/5">
              Logout
            </button>
          </form>
        </div>
      </div>
    </header>
  );
}
