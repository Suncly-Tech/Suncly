import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { site } from "@/lib/content";
import "./globals.css";

const display = localFont({
  src: "./fonts/InstrumentSerif-Regular-latin.woff2",
  weight: "400",
  style: "normal",
  variable: "--font-instrument-serif",
  display: "swap",
  fallback: ["Georgia", "Times New Roman", "serif"],
});

const sans = localFont({
  src: "./fonts/Manrope-Variable-latin.woff2",
  weight: "200 800",
  style: "normal",
  variable: "--font-manrope",
  display: "swap",
  fallback: ["system-ui", "Helvetica Neue", "Arial", "sans-serif"],
});

const mono = localFont({
  src: "./fonts/JetBrainsMono-Variable-latin.woff2",
  weight: "100 800",
  style: "normal",
  variable: "--font-jetbrains-mono",
  display: "swap",
  fallback: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
});

export const metadata: Metadata = {
  metadataBase: new URL(site.domain),
  title: {
    default: site.title,
    template: "%s — Suncly",
  },
  description: site.description,
  openGraph: {
    type: "website",
    siteName: "Suncly",
    title: site.title,
    description: site.description,
    url: site.domain,
    images: [{ url: "/og.png", width: 1200, height: 630, alt: "Suncly" }],
  },
  twitter: {
    card: "summary_large_image",
    title: site.title,
    description: site.description,
    images: ["/og.png"],
  },
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
  alternates: { canonical: "/" },
};

export const viewport: Viewport = {
  themeColor: "#3461D1",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${mono.variable}`}>
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
