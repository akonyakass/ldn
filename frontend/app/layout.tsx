import type { Metadata } from "next";
import localFont from "next/font/local";
import { DashboardShell } from "@/components/dashboard-shell";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "ClaudeIntel — Growth Intelligence Engine",
  description:
    "Reverse-engineering Claude's viral growth — discourse intelligence for growth teams",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-[family-name:var(--font-geist-sans)] antialiased`}
      >
        <DashboardShell>{children}</DashboardShell>
      </body>
    </html>
  );
}
