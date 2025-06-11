"use client";

import type { Metadata } from "next";
import { useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { Scripts } from "@/components/shared/scripts";
import { SideNav } from "@/components/side-nav";
import { Breadcrumbs } from "@/components/shared/breadcrumbs";
import { PageHeader } from "@/components/headers/page-header";
import { purchases } from "@/data";
import { Line } from "@/components/tables/line";
import { usePurchaseStore } from "@/store/purchase";
import { calculateDateByDays } from "@/utils";
import type { IPurchase } from "@/types/data";

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

interface ITabButton {
  isActive: boolean;
  target: string;
  label: string;
}

export default function PurchasesPage() {
  // const [purchaseList, setPurchaseList] = useState<IPurchase[]>([]);
  const { purchaseList, setPurchaseList } = usePurchaseStore((state) => state);
  const [tabsButtonList, setTabsButtonList] = useState<ITabButton[]>([
    { isActive: true, target: "All", label: "All" },
    { isActive: false, target: "Proxy", label: "Proxy" },
    { isActive: false, target: "Accounts", label: "Accounts" },
    { isActive: false, target: "Services", label: "Services" },
  ]);

  // useEffect(() => {
  //   setPurchaseList(purchases);
  // }, []);

  const handleTabButtonClick = (target: string) => {
    setTabsButtonList(
      tabsButtonList.map((item) => ({
        ...item,
        isActive: item.target === target
      }))
    )
  };

  return (
    <div className="page__wrapper">
      <SideNav />
      <div className="main__content">
        <div id="auth-header-box">
          <Header />
        </div>
        <main>
          <Breadcrumbs name="My purchases" />
          <PageHeader name="My purchases" />
          <section id="tabData" className="contentFilter container">
            <div className="tabs">
              <div className="tabs__nav">
                {tabsButtonList.map(({ isActive, target, label }) => (
                  <button
                    key={uuidv4()}
                    className={`tabs__button ${isActive ? "active" : ""}`}
                    data-tab={target}
                    onClick={() => handleTabButtonClick(target)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className="tabs__content">
                <div className="table__head">
                  <div className="head__title">Name</div>
                  <div className="head__title">Amount</div>
                  <div className="head__title">Dates</div>
                  <div className="head__title">Action</div>
                </div>

                <div className="table__content">
                  {purchaseList.map(
                    ({
                      id,
                      name,
                      minQuantity,
                      maxQuantity,
                      durationDays,
                      proxyCategory,
                    }) => (
                      <div
                        key={id}
                        className="element__line activated"
                        data-category="All Proxy"
                      >
                        <div className="content__data">
                          <span className="name">{name}</span>
                          <span className="value green">
                            {minQuantity} / {maxQuantity}
                          </span>
                          <span className="value green">
                            {calculateDateByDays(Math.abs(30 - durationDays), "-")} / {durationDays}
                          </span>
                          <div className="actions">
                            <button type="button">
                              <i className="ico-cart"></i>
                            </button>
                            <a href="#" title="name">
                              <i className="ico-eye"></i>
                            </a>
                          </div>
                        </div>
                        <div className="mainData">
                          <span className="service">{proxyCategory}</span>
                          <span className="shop">NVS Shop</span>
                        </div>
                      </div>
                    )
                  )}
                  {/* {purchaseList.map(({ active, name, category, shop }) => {
                    // return active
                    //   ? <Line active />
                    //   : <Line />
                    return <div></div>;
                  })} */}
                </div>
              </div>
            </div>
          </section>
        </main>
        <Footer />
        <Scripts />
      </div>
    </div>
  );
}
