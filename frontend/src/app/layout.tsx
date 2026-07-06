import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trading Agent",
  description: "Backtest dashboard for the conservative trading agent"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
