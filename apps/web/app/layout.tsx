import type { Metadata } from "next";
import "@fontsource-variable/noto-sans-sc";
import "./globals.css";
import { Providers } from "@/components/providers";
export const metadata: Metadata = {
  title: "LATTICE · Verified financial orchestration",
  description: "Every commitment. Every source. A plan you can verify.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
