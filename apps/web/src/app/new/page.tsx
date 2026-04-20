import Link from 'next/link';
import { createSupabaseServerClient } from '@/lib/supabase/server';
import { listClients, listJobs } from '@/lib/db/jobs';
import { TopBar } from '@/components/TopBar';
import { NewJobForm } from './_components/NewJobForm';

export default async function NewJobPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const [clients, recentJobs] = await Promise.all([listClients(), listJobs(200)]);
  const succeededJobs = recentJobs.filter(
    (j) => j.status === 'succeeded' || j.status === 'completed_with_warnings',
  );

  return (
    <>
      <TopBar email={user?.email ?? undefined} />
      <main className="mx-auto max-w-3xl px-6 py-10">
        <div className="mb-6">
          <Link
            href="/"
            className="text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
          >
            ← Zurück
          </Link>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">Neue Research</h1>
          <p className="mt-1 text-sm text-[var(--color-text-muted)]">
            Kunde + Modus wählen, Angle eingeben, starten. Fortschritt läuft live in der Job-Ansicht.
          </p>
        </div>

        {clients.length === 0 ? (
          <div className="card p-8 text-center text-sm text-[var(--color-text-muted)]">
            Keine Kunden in der Datenbank. Bitte erst in der <code>public.clients</code>-Tabelle
            anlegen.
          </div>
        ) : (
          <NewJobForm clients={clients} priorJobs={succeededJobs} />
        )}
      </main>
    </>
  );
}
