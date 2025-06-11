"use client"

import type { Metadata } from "next";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { SideNav } from "@/components/side-nav";
import { InputPlacetop } from "@/components/shared/forms/input-placetop";
import { Breadcrumbs } from "@/components/shared/breadcrumbs";
import { Footer } from "@/components/layout/footer";
import { Scripts } from "@/components/shared/scripts";
import { useAuthStore } from "@/store/auth";

// export const metadata: Metadata = {
//   title: "GEMUPS",
//   description: "",
//   keywords: "",
//   openGraph: {
//     type: "website",
//     url: "",
//     description: "",
//     siteName: "",
//     images: "",
//   },
// };

interface ILoginFormData {
  email: string
  password: string
}

export default function LoginPage() {
  const router = useRouter();
  
    const { isAuth, isLoading, isError, error, login } = useAuthStore((state) => state);
    const [submitAccess, setSubmitAccess] = useState<boolean>(false);
    const [formData, setFormData] = useState<ILoginFormData>({
      email: "",
      password: ""
    });
    
    useEffect(() => {
      if (isAuth) {
        router.push("/");
      }
    }, [isAuth]);
  
    useEffect(() => {
      const { email, password } = formData;
      if (email.length > 0 && password.length > 0) {
        setSubmitAccess(true);
      } else {
        setSubmitAccess(false);
      }
    }, [formData]);
  
    const handleSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      
      const { email, password } = formData;
      await login(email, password);
      if (isError) {
        console.log(error);
        const prefix = error?.message ? `${error.message} ` : "";
        alert(`${prefix}\nPlease try again`)
      }
    }

  return (
    <div className="page__wrapper">
      <SideNav />
      <div className="main__content">
        <div id="auth-header-box">
          <Header />
        </div>
        <main>
          <Breadcrumbs name="Login" />
          <div className="fullscreen container">
            <div className="form__wrapper">
              <div className="form__header">
                <h1>Login</h1>
                <p>Дополнительный вспомогательный текст при необходимости.</p>
              </div>
              <form className="formBody" id="auth" data-form-type="login" onSubmit={handleSubmit}>
                <div className="form__fields">
                  <InputPlacetop
                    id="username-email"
                    type="text"
                    name="email"
                    placeholder=""
                    label="Email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                  />
                  <InputPlacetop
                    id="password"
                    type="password"
                    name="password"
                    placeholder="Password"
                    label="Password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required
                  />
                </div>

                <div className="form__action">
                  <button type="submit" disabled={isLoading}>Login</button>
                  <div className="sub__actions">
                    <Link href="/register">Don't have an account ?</Link>
                    <Link href="#" data-hystmodal="#forgotPassword">
                      Forgot password
                    </Link>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </main>
        <Footer />
        <Scripts />  
      </div>
    </div>
  );
}
