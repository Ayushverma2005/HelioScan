import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HelioScan",
  description: "HelioScan frontend (under development)",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-gray-400 p-4">
          <h1 className="text-2xl font-bold">HelioScan</h1>
        </header>
        <main className="mx-auto max-w-2xl p-4">{children}</main>
      </body>
    </html>
  );
}