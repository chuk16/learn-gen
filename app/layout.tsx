import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "./globals.css";
import { cn } from "@/lib/utils";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap"
});

export const metadata: Metadata = {
  title: "Learn Gen",
  description:
    "Create polished explainer videos with AI powered storytelling, visuals, and narration."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={cn(
          "min-h-screen bg-background font-sans text-foreground",
          inter.variable
        )}
      >
        {children}
      </body>
    </html>
  );
}
