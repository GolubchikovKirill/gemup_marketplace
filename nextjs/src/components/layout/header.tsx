"use client";

import Link from "next/link";
import { useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import LangSwitch from "../shared/header/lang-switch";
import Burger from "../shared/header/burger";
import Cart from "../shared/header/cart";
import { CartModal } from "../shared/modals/cart";
import AuthActions from "../shared/header/auth-actions";
import { useAuth } from "@/hooks/auth";
import { useAuthStore } from "@/store/auth";
import { useCartStore } from "@/store/cart";
import { useSettingsStore } from "@/store/settings";

export const Header: React.FC = () => {
  const { isAuth } = useAuth();
  const { user, logout } = useAuthStore((state) => state);
  const { isMenuOpen, setValue: setSettingsValue } = useSettingsStore(
    (state) => state
  );

  const menuItemList = [
    { id: uuidv4(), ico: "ico-user", label: "My Profile", href: "/profile" },
    {
      id: uuidv4(),
      ico: "ico-cart-bag",
      label: "My Purchases",
      href: "/purchases",
    },
    {
      id: uuidv4(),
      ico: "ico-arrow-menu-left",
      label: "Transactions",
      href: "/transactions",
    },
    { id: uuidv4(), ico: "ico-tag", label: "Seller", href: "/seller" },
    { id: uuidv4(), ico: "ico-users", label: "Referral", href: "/referral" },
    { id: uuidv4(), ico: "ico-logout", label: "Logout", href: "/" },
  ];

  useEffect(() => {
    console.log(isMenuOpen);
  }, [isMenuOpen]);

  if (isAuth) {
    return (
      <header className="auth">
        <div className="header__wrapper">
          <div className="leftSide">
            <a href="#" title="name">
              <img src="/img/logo/logo_icon.svg" alt="name" />
            </a>
          </div>
          <div className="rightSide">
            <LangSwitch />
            <div className="cash__wrapper">
              <i className="ico-wallet"></i>
              <a href="#" className="billing">
                <span className="value">
                  {user?.balance ? parseFloat(user.balance).toFixed(2) : ""}
                </span>
                <span className="currency">$</span>
              </a>
            </div>
            <div className="user__wrapper">
              <div className="user__name">
                <i className="ico-user"></i>
                <span>{user?.username}</span>
              </div>
              <i className="ico-arrow"></i>
              <div className="userMenu">
                <ul className="userMenu__items">
                  {menuItemList.map(({ id, ico, label, href }) => (
                    <li className="userMenu__item" key={id}>
                      <Link
                        href={href}
                        title=""
                        onClick={
                          label.toLowerCase() === "logout" ? logout : () => null
                        }
                      >
                        <i className={ico}></i>
                        {label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <Cart />
            <Burger />
          </div>
          <div className={`mobileMenu__wrapper ${isMenuOpen ? "active" : ""}`}>
            <div className="head__area">
              <LangSwitch />
              <button
                className="closeMenu"
                onClick={() => setSettingsValue("isMenuOpen", false)}
              >
                <i className="ico-close"></i>
              </button>
            </div>
            <div className="mainMenu__wrapper">
              <div className="menu__element">
                <span className="menuHead">Menu</span>
                <nav className="mobNav__wrapper">
                  <ul className="mobNav">
                    <li className="mobNav__item">
                      <i className="ico-shield"></i>
                      <a href="#" title="name">
                        Proxy
                      </a>
                    </li>
                  </ul>
                </nav>
              </div>
              <div className="menu__element">
                <span className="menuHead">Support</span>
                <nav className="mobNav__wrapper">
                  <ul className="mobNav">
                    <li className="mobNav__item">
                      <i className="ico-details"></i>
                      <a href="#" title="name">
                        Help
                      </a>
                    </li>
                  </ul>
                </nav>
              </div>
            </div>
          </div>
        </div>
        <CartModal />
      </header>
    );
  }

  return (
    <header className="noauth">
      <div className="header__wrapper">
        <div className="leftSide">
          <a href="#" title="name">
            <img src="/img/logo/logo_icon.svg" alt="name" />
          </a>
        </div>
        <div className="rightSide">
          <LangSwitch />
          <AuthActions />
          <Cart />
          <Burger />
        </div>
        <div className="mobileMenu__wrapper">
          <div className="head__area">
            <LangSwitch />
            <button
              className="closeMenu"
              onClick={() => setSettingsValue("isMenuOpen", false)}
            >
              <i className="ico-close"></i>
            </button>
          </div>
          <div className="mainMenu__wrapper">
            <div className="menu__element">
              <span className="menuHead">Menu</span>
              <nav className="mobNav__wrapper">
                <ul className="mobNav">
                  <li className="mobNav__item">
                    <i className="ico-shield"></i>
                    <a href="#" title="name">
                      Proxy
                    </a>
                  </li>
                </ul>
              </nav>
            </div>
            <div className="menu__element">
              <span className="menuHead">Support</span>
              <nav className="mobNav__wrapper">
                <ul className="mobNav">
                  <li className="mobNav__item">
                    <i className="ico-details"></i>
                    <a href="#" title="name">
                      Help
                    </a>
                  </li>
                </ul>
              </nav>
            </div>
          </div>
        </div>
      </div>
      <CartModal />
    </header>
  );
};
