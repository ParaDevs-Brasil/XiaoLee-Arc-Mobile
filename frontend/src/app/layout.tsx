import type { Metadata } from "next";
import "./globals.css";
import { Quicksand } from "next/font/google";
import localFont from "next/font/local";
import { ThemeProviderWrapper } from "../providers/ThemeProvider";
import { LanguageProvider } from "../contexts/LanguageContext";

const quicksand = Quicksand({
  subsets: ["latin"],
  variable: "--font-quicksand",
  weight: ["300", "400", "500", "600", "700"]
});

// Fonte do logo (navbar do app) — Candice, carregada localmente.
// candice-web.ttf é o subset latino re-serializado: o TTF original (conversão
// antiga da URW) tinha tabelas glyf/hmtx malformadas e era rejeitado pelo
// sanitizador OTS dos navegadores.
const candice = localFont({
  src: "../fonts/candice-web.ttf",
  variable: "--font-candice",
  display: "swap",
});


export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export const metadata: Metadata = {
    title: "✨ Xiaolee - Cute AI Chat 💖",
    description: "Um chat super fofo com uma assistente IA kawaii! (◕‿◕)♡",
    other: {
        'preload-video-1': '/xiaolee_cheer.mov',
        'preload-video-2': '/xiaolee_giggle.mp4',
        'preload-video-3': '/xiaolee_idle.mp4',
        'preload-video-4': '/xiaolee_wave.mp4',
        'preload-video-5': '/xiaolee_kawaii.mov',
        'preload-video-6': '/xiaolee_love.mp4',
        'preload-video-7': '/xiaolee_ola.mov',
        'preload-video-8': '/xiaolee_standby.mov',
        'preload-video-9': '/xiaolee_standby2.mov',
        'preload-video-10': '/xiaolee_standby3.mov',
        'preload-video-11': '/xiaolee_surprise.mov',
        'preload-video-12': '/xiaolee_thinklow.mov',
        'preload-video-13': '/xiaolee_uncomfortable.mov',
        'preload-video-14': '/xiaolee_ouch.mov',
        'preload-video-15': '/xiaolee_salute.mov'
    }
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="pt-BR" suppressHydrationWarning>
            <head>
                <link rel="icon" href="/favicon.ico" sizes="any" />
                <link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png" />
                <link rel="icon" type="image/png" sizes="512x512" href="/icon-512.png" />
                <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
                <link rel="preload" as="video" href="/xiaolee_standby.mov" />
            </head>
                <body className={`${quicksand.className} ${candice.variable}`}>
                <LanguageProvider>
                  <ThemeProviderWrapper>
                      {children}
                  </ThemeProviderWrapper>
                </LanguageProvider>
            </body>
        </html>
    );
}