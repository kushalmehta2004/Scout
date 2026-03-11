import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Scout — Job & Internship Discovery",
  description: "AI-powered job and internship discovery",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
