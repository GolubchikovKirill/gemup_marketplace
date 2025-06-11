import type { Metadata } from "next";
import type { Viewport } from "next";
import { AuthProvider } from "@/providers/auth";
import { SettingsProvider } from "@/providers/settings";
import { Inter } from "next/font/google";
import "./globals.scss";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: 'swap',
  weight: ["400", "500", "600", "700"]
});

export const metadata: Metadata = {
  title: "GEMUPS",
  description: ""
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1.0,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.variable}>
        <SettingsProvider>
          <AuthProvider>
            {children}
          </AuthProvider>
        </SettingsProvider>
      </body>
    </html>
  );
}
