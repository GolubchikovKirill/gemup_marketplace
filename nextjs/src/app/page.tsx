import type { Metadata } from "next";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { Scripts } from "@/components/shared/scripts";
import { SideNav } from "@/components/side-nav";
import styles from "./page.module.scss";

export const metadata: Metadata = {
  title: "GEMUPS",
  description: "",
  keywords: "",
  openGraph: {
    type: "website",
    url: "",
    description: "",
    siteName: "",
    images: "",
  },
};

export default function Home() {
  return (
    <div className="page__wrapper">
      <SideNav />
      <div className="main__content">
        <div id="auth-header-box">
          <Header />
        </div>
        <main>
          <h1>Content</h1>
        </main>
        <Footer />
        <Scripts />
      </div>
    </div>
  );
}
