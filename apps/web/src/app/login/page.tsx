import { LoginButton } from './_components/LoginButton';

type SearchParams = Promise<{ error?: string; next?: string }>;

export default async function LoginPage({ searchParams }: { searchParams: SearchParams }) {
  const { error, next } = await searchParams;

  return (
    <main className="grid min-h-screen place-items-center px-4">
      <div className="card w-full max-w-md p-8">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold tracking-tight">ecomtorials Research Hub</h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Intern. Nur für Konten mit <code>@ecomtorials.de</code>.
          </p>
        </div>

        {error === 'domain' && (
          <div className="mb-4 rounded-md border border-red-900/50 bg-red-950/40 px-3 py-2 text-sm text-red-200">
            Dein Google-Konto ist nicht <code>@ecomtorials.de</code>. Bitte mit dem Firmen-Account einloggen.
          </div>
        )}

        <LoginButton next={next} />
      </div>
    </main>
  );
}
