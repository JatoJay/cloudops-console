import type { Metadata } from "next";
import type { ReactNode } from "react";
import "@fontsource-variable/manrope";
import "@fontsource/ibm-plex-mono/400.css";
import "./globals.css";

import { QueryProvider } from "@/components/query-provider";

export const metadata: Metadata = {
  title: "CloudOps Console",
  description: "Cloud troubleshooting, security scanning, and AI-powered cost optimization.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
