import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "VOC Hub",
  description: "VOC evidence operations workspace"
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="zh-CN">
      <body>
        <a className="skipLink" href="#main-content">
          跳到主内容
        </a>
        {children}
      </body>
    </html>
  );
}
