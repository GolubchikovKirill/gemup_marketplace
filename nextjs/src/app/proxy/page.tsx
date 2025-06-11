"use client";

import type { Metadata } from "next";
import { useEffect, useState } from "react";
import axios from "axios";
import { v4 as uuidv4 } from "uuid";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { Scripts } from "@/components/shared/scripts";
import { SideNav } from "@/components/side-nav";
import { Breadcrumbs } from "@/components/shared/breadcrumbs";
import { PageHeader } from "@/components/headers/page-header";
import { ProductItem } from "@/components/product-item";
import { proxyProducts } from "@/data";
import { IProxyProduct, ISellerProduct } from "@/types/data";
import { useProductStore } from "@/store/product";
import { usePurchaseStore } from "@/store/purchase";

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

interface IProxyCategory {
  id: string | number;
  isActive: boolean;
  label: string;
}

export default function ProxyPage() {
  const { productList, getProductList } = useProductStore((state) => state);
  const { purchaseList } = usePurchaseStore((state) => state);

  const [isAllProxyCategory, setIsAllProxyCategory] = useState<boolean>(true);
  const [currentProxyCategoryList, setCurrentProxyCategoryList] = useState<
    string[]
  >(["Residential"]);
  const [proxyCategoryList, setProxyCategoryList] = useState<IProxyCategory[]>([
    { id: uuidv4(), isActive: false, label: "Residential" },
    { id: uuidv4(), isActive: false, label: "Isp" },
    { id: uuidv4(), isActive: false, label: "Datacenter" },
    { id: uuidv4(), isActive: false, label: "Nodepay" },
    { id: uuidv4(), isActive: false, label: "Grass" },
  ]);

  useEffect(() => {
    getProductList(purchaseList);
  }, []);

  useEffect(() => {
    const activeCategoryList = proxyCategoryList.filter((item) => item.isActive);

    setCurrentProxyCategoryList(
      proxyCategoryList
        .filter((item) => item.isActive)
        .map((item) => item.label)
    );
  }, [proxyCategoryList]);

  useEffect(() => {
    setProxyCategoryList(
      proxyCategoryList.map((item) => ({ ...item, isActive: isAllProxyCategory }))
    )
  }, [isAllProxyCategory]);

  const setCategory = (label: string) => {
    setProxyCategoryList(
      proxyCategoryList.map((item) => ({
        ...item,
        isActive:
          item.label === label
            ? !item.isActive
            : item.isActive,
      }))
    );
  };

  return (
    <div className="page__wrapper">
      <SideNav />
      <div className="main__content">
        <div id="auth-header-box">
          <Header />
        </div>
        <main>
          <Breadcrumbs name="Proxy" />
          <PageHeader name="Proxy" />
          <div className="product__filters container">
            <div className="filter__tags">
              {proxyCategoryList.map(({ id, isActive, label }) => (
                <button
                  key={id}
                  data-filter={label}
                  className={`filter-btn ${isActive && "active"}`}
                  onClick={() => setCategory(label)}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="full__filters">
              <button
                style={isAllProxyCategory ? { color: "#13F195", backgroundColor: "rgba(19, 241, 149, 0.1019607843)" } : {}}
                className={`see-all ${isAllProxyCategory && "active"}`}
                onClick={() => setIsAllProxyCategory(!isAllProxyCategory)}
              >
                See all
              </button>
            </div>
          </div>

          <section className="container" id="products__container">
            {proxyCategoryList.map(({ isActive, label }) => (  
              isActive && <div className="product__category" data-tags={label}>
                <div className="head__block">
                  <h2 className="category__title">{label}</h2>
                </div>
                <div className="products__items">
                  {productList
                    .filter(
                      (item) => item.proxyCategory.toLowerCase() === label.toLowerCase()
                    )
                    .map((data) => (
                      <ProductItem key={data.id} {...data} />
                    ))}
                </div>
              </div>
            ))}
          </section>
        </main>
        <Footer />
        <Scripts />
      </div>
    </div>
  );
}
