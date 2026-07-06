import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CrickAI Intelligence",
  description: "Multi-agent cricket intelligence platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="bg-slate-950 text-slate-200">
      <body className={`${inter.className} min-h-screen flex flex-col overflow-x-hidden`}>
        <Navbar />
        <main className="flex-1 w-full max-w-6xl mx-auto p-6">
          {children}
        </main>
      </body>
    </html>
  );
}