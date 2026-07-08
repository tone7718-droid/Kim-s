import type { Metadata, Viewport } from "next";
import { ServiceWorkerRegistration } from "@/components/ServiceWorkerRegistration";
import "./globals.css";

export const metadata: Metadata = {
  title: "KBO 직관 승률",
  description: "KBO 직관 경기 승률 자동 계산기",
  manifest: "/manifest.webmanifest",
  applicationName: "KBO 직관 승률",
  appleWebApp: {
    capable: true,
    title: "KBO 직관 승률",
    statusBarStyle: "default",
  },
};

export const viewport: Viewport = {
  themeColor: "#18181b",
  width: "device-width",
  initialScale: 1,
  // Intentionally allow pinch-zoom (no maximumScale / userScalable:false):
  // blocking zoom fails WCAG 1.4.4, and iOS Safari ignores those flags
  // anyway, so disabling them costs nothing in UX.
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen">
        <ServiceWorkerRegistration />
        {children}
      </body>
    </html>
  );
}
