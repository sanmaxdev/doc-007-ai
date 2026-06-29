import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DOC-007-AI",
  description:
    "Multi-tenant AI knowledge base — upload documents, ask questions, get cited, grounded answers.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
