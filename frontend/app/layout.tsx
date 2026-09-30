import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AnimatedBackground } from "@/components/AnimatedBackground";
import { MobileNav, Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "УУНиТ — База знаний студентов",
  description: "ИИ-консультант, который отвечает на вопросы студентов и указывает источник.",
};

// viewport-fit=cover - чтобы env(safe-area-inset-*) работали под «чёлкой» и полоской жестов
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#050b24",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <AnimatedBackground />
        <div className="layout">
          <Sidebar />
          <main className="main">
            {children}
          </main>
        </div>
        <MobileNav />
      </body>
    </html>
  );
}
