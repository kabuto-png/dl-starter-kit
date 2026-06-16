import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AKC Demo — Agent Knowledge Core",
  description:
    "Interactive demo for the Agent Knowledge Core (AKC) — team memory system for ASO specialists at VNG Publishing.",
  openGraph: {
    title: "AKC Demo — Agent Knowledge Core",
    description: "Test AKC memory recall + Gemma LLM in your browser.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="h-full bg-[#0f1117] text-[#e6edf3] antialiased">
        {children}
      </body>
    </html>
  );
}
