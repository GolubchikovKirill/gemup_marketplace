"use client"

import type { Metadata } from "next";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { Scripts } from "@/components/shared/scripts";
import { SideNav } from "@/components/side-nav";
import { Breadcrumbs } from "@/components/shared/breadcrumbs";
import { InputPlacetop } from "@/components/shared/forms/input-placetop";
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

interface IRegisterFormData {
  username: string
  email: string
  password: string
  referralCode?: string
}

export default function RegisterPage() {
  const router = useRouter();

  const { isLoading, isError, error, user, register } = useAuthStore((state) => state);
  const [submitAccess, setSubmitAccess] = useState<boolean>(false);
  const [formData, setFormData] = useState<IRegisterFormData>({
    username: "",
    email: "",
    password: "",
    referralCode: ""
  });

  useEffect(() => {
    const { username, email, password } = formData;
    if (username.length > 0 && email.length > 0 && password.length > 0) {
      setSubmitAccess(true);
    } else {
      setSubmitAccess(false);
    }
  }, [formData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const { username, email, password, referralCode } = formData;
    await register(username, email, password, referralCode);
    if (isError) {
      const prefix = error?.message ? `${error.message} ` : "";
      alert(`${prefix}\nPlease try again`);
    }

    if (!isLoading && !isError) {
      alert("Registration successfully completed");
      setFormData({
        username: "",
        email: "",
        password: "",
        referralCode: ""
      });
      router.push("/login");
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
          <Breadcrumbs name="Register" />
          <div className="fullscreen container">
            <div className="form__wrapper">
              <div className="form__header">
                <h1>Register</h1>
                <p>Дополнительный вспомогательный текст при необходимости.</p>
              </div>
              <form
                className="formBody form"
                id="auth"
                data-form-type="register"
                onSubmit={handleSubmit}
              >
                <div className="form__fields">
                  <InputPlacetop
                    id="Username"
                    type="text"
                    name="username"
                    placeholder="Username"
                    label="Username"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    required
                  />
                  <InputPlacetop
                    id="email"
                    type="email"
                    name="email"
                    placeholder="Email"
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
                  <InputPlacetop
                    id="referral"
                    type="text"
                    name="referral"
                    placeholder="Referral Code (Optional)"
                    label="Referral Code (Optional)"
                    value={formData.referralCode}
                    onChange={(e) => setFormData({ ...formData, referralCode: e.target.value })}
                  />
                </div>

                <div className="form__action">
                  <button type="submit" disabled={isLoading}>
                    Register
                  </button>
                  <div className="sub__actions">
                    <Link href="/login">Already have an account ?</Link>
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
