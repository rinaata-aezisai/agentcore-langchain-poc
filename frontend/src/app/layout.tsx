import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Sidebar } from "@/widgets/sidebar";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "AgentCore vs LangChain PoC",
  description: "AWS Bedrock AgentCore and LangChain comparison dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body className={`${inter.variable} font-sans antialiased`}>
        <Providers>
          <div className="flex min-h-screen bg-slate-900">
            <Sidebar />
            <main className="flex-1 ml-64">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
