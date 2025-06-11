"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSettingsStore } from "@/store/settings";

export const SideNav: React.FC = () => {
  const { isSidebarOpen, setValue } = useSettingsStore();

  return (
    <div className={`fixedNavmenu ${!isSidebarOpen && "closed"}`}>
      <div className="head__block">
        <div className="logo__wrapper">
          <Link href="/" title="main">
            <img
              className="logo__element"
              src="/img/logo/logo_icon.svg"
              alt="name"
            />
            <img
              className="logo__text"
              src="/img/logo/logo_text.svg"
              alt="name"
            />
          </Link>
        </div>
        <button
          className="menuFunction"
          type="button"
          onClick={() => setValue("isSidebarOpen", false)}
        >
          <i className="ico-burger-nav"></i>
        </button>
        <button
          className={`menuMinimal ${isSidebarOpen && "hidden"}`}
          type="button"
          onClick={() => setValue("isSidebarOpen", true)}
        >
          <i className="ico-burger-mb"></i>
        </button>
      </div>

      <div className="sidebar__element">
        <div className="headline">Menu</div>
        <nav className="sidebarNav">
          <ul>
            <li className="sidenav__element active">
              <span>
                <i className="ico-category"></i>
              </span>
            </li>
            <li className="sidenav__element collapsed">
              <button type="button">
                <div className="name">
                  <i className="ico-users"></i>
                  Accounts
                </div>
                <i className="ico-arrow"></i>
              </button>
            </li>
            <li className="sidenav__element">
              <Link href="/proxy" title="name">
                <i className="ico-shield"></i>Proxy
              </Link>
            </li>
          </ul>
        </nav>
      </div>

      <div className="sidebar__element">
        <div className="headline">General</div>
        <nav className="sidebarNav">
          <ul>
            <li className="sidenav__element">
              <a href="#" title="name">
                <i className="ico-refresh"></i>History
              </a>
            </li>
            <li className="sidenav__element">
              <a href="#" title="name">
                <i className="ico-details"></i>Help
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </div>
  );
};
