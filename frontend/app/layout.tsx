import type { Metadata } from "next";
import "./globals.css";
import { AnimatedBackground } from "@/components/AnimatedBackground";
import { Sidebar } from "@/components/Sidebar";
import { UserMenu } from "@/components/UserMenu";

export const metadata: Metadata = {
  title: "УУНиТ — База знаний студентов",
  description: "ИИ-консультант, который отвечает на вопросы студентов и указывает источник.",
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
            <UserMenu />
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
