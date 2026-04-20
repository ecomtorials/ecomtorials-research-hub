'use client';

import { useState } from 'react';
import { createSupabaseBrowserClient } from '@/lib/supabase/browser';

export function LoginButton({ next }: { next?: string }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onClick() {
    setLoading(true);
    setError(null);
    const supabase = createSupabaseBrowserClient();
    const redirectTo = `${window.location.origin}/auth/callback${next ? `?next=${encodeURIComponent(next)}` : ''}`;
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo,
        queryParams: {
          hd: 'ecomtorials.de',
          prompt: 'select_account',
        },
      },
    });
    if (error) {
      setError(error.message);
      setLoading(false);
    }
  }

  return (
    <>
      <button
        onClick={onClick}
        disabled={loading}
        className="flex w-full items-center justify-center gap-3 rounded-md border border-[var(--color-border)] bg-white px-4 py-2.5 text-sm font-medium text-zinc-900 transition hover:bg-zinc-100 disabled:opacity-50"
      >
        <GoogleLogo />
        {loading ? 'Weiterleiten…' : 'Mit Google fortfahren'}
      </button>
      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
    </>
  );
}

function GoogleLogo() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.5 12.27c0-.79-.07-1.54-.2-2.27H12v4.3h5.9a5.05 5.05 0 0 1-2.19 3.31v2.74h3.54c2.07-1.91 3.25-4.72 3.25-8.08Z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.95 0 5.42-.98 7.23-2.65l-3.54-2.74c-.98.66-2.23 1.05-3.69 1.05-2.84 0-5.25-1.92-6.11-4.5H2.24v2.83A10.99 10.99 0 0 0 12 23Z"
      />
      <path
        fill="#FBBC05"
        d="M5.89 14.16a6.6 6.6 0 0 1 0-4.32V7H2.24a11 11 0 0 0 0 9.99l3.65-2.83Z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.61 0 3.05.55 4.19 1.64l3.14-3.14C17.41 2.09 14.95 1 12 1 7.7 1 3.99 3.47 2.24 7l3.65 2.83C6.75 7.3 9.16 5.38 12 5.38Z"
      />
    </svg>
  );
}
