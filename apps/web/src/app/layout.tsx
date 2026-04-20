import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ecomtorials Research Hub',
  description: 'Research-Reports für D2C-Advertorials — Full, Angle, UMP/UMS und Custom.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
