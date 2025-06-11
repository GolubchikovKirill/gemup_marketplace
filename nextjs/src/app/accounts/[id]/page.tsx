"use client";

import type { Metadata } from "next";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { PageHeader } from "@/components/headers/page-header";
import { Header } from "@/components/layout/header";
import { Breadcrumbs } from "@/components/shared/breadcrumbs";
import { CommentItem } from "@/components/shared/comment-item";
import { SideNav } from "@/components/side-nav";
import { marketplaceComments } from "@/data";
import type { ICommentItem } from "@/types/component";
import { Footer } from "@/components/layout/footer";
import { Scripts } from "@/components/shared/scripts";
import { UnverifiedBox } from "@/components/shared/unverified-box";
import { useAuthStore } from "@/store/auth";
import { useProductStore } from "@/store/product";

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

export default function AccountsPage() {
  const { user } = useAuthStore((state) => state);
  const { productList } = useProductStore();

  const [comments, setComments] = useState<ICommentItem[]>([]);

  const pathname = usePathname();
  const pathnameItems = pathname.split("/");
  const id = pathnameItems[pathnameItems.length - 1];

  useEffect(() => {
    setComments(marketplaceComments.accounts);
  }, []);

  return (
    <div className="page__wrapper">
      <SideNav />
      <div className="main__content">
        <div id="auth-header-box">
          <Header />
        </div>
        <main>
          <Breadcrumbs name="Accounts" />
          <PageHeader name="Accounts" />
          {!user?.isVerified && <UnverifiedBox />}
          <div className="innerContent__wrapper container">
            <div className="mainContent">
              <section id="account__data">
                <div className="accountData__wrapper">
                  <div className="avatar">
                    <div className="img__wrapper">
                      <img src="/img/tests/ava.png" alt="name" />
                      <i className="ico-shield"></i>
                    </div>
                  </div>
                  <div className="content">
                    <h2 className="name">
                      Аккаунты Twitter | 2FA | Добавлена аватарка | Сделан
                      первый твит | Подтверждены
                    </h2>
                    <div className="textarea">
                      <p>200+ countries</p>
                      <p>Fast loading sites</p>
                      <p>No blocking or restrictions</p>
                    </div>
                    <div className="tags__wrapper">
                      <span className="tag">Twitter</span>
                      <span className="tag">2FA</span>
                      <span className="tag">Tdata</span>
                      <span className="tag">Session</span>
                      <span className="tag">json</span>
                      <span className="tag">Tdata</span>
                    </div>
                    <div className="rating__area">
                      <div className="rating">
                        <div className="stars__wrapper">
                          <i className="ico-star active"></i>
                          <i className="ico-star active"></i>
                          <i className="ico-star active"></i>
                          <i className="ico-star active"></i>
                          <i className="ico-star active"></i>
                        </div>
                        <span className="value">5/5</span>
                      </div>
                      <span className="delimiter"></span>
                      <div className="sales__wrapper">
                        <span className="value">242523</span>
                        <span className="name">Sales</span>
                      </div>
                    </div>
                  </div>
                  <div className="actions">
                    <button className="copy-link">
                      <i className="ico-copy"></i>Copy link
                    </button>
                  </div>
                </div>
              </section>
              <section id="tabData">
                <div className="tabs">
                  <div className="tabs__nav">
                    <button className="tabs__button active" data-tab="Overview">
                      Overview
                    </button>
                    <button className="tabs__button" data-tab="Reviews">
                      Reviews
                    </button>
                  </div>
                  <div className="tabs__content">
                    <div className="tab active" id="Overview">
                      <section id="description__block">
                        <div className="description__wrapper">
                          <div className="title">Description</div>
                          <div className="content__body">
                            <p>Unlimited IPs + Sessions. Pay only for gb.</p>
                            <p>
                              ⭐️ TELEGRAM АНГЛИЯ ⭐️ TDATA + SESSION+JSON ⭐️ 1
                              ACS IN A PACK
                            </p>
                            <ul>
                              <li>Пол: Mix</li>
                              <li>Возраст: Mix</li>
                              <li>
                                Работает совместно с Telegram Portable и другими
                                софтами на Teleton
                              </li>
                              <li>
                                В архиве находиться 2 файла, tdata и
                                session+json
                              </li>
                              <li>Если запускать много - используйте proxy</li>
                              <li>
                                На аккаунтах 2FA, пароль находиться в архиве в
                                файле twoFA.txt
                              </li>
                            </ul>
                          </div>
                          <button type="button">More</button>
                        </div>
                      </section>
                    </div>
                    <div className="tab" id="Reviews">
                      <section id="Average__seller">
                        <div className="average__wrapper">
                          <div className="leftSIde">
                            <div className="title">
                              Average seller rate 5 (289)
                            </div>
                            <div className="rating__wrapper">
                              <span className="value">5.0</span>
                              <div className="rating__stars">
                                <i className="ico-star active"></i>
                                <i className="ico-star active"></i>
                                <i className="ico-star active"></i>
                                <i className="ico-star active"></i>
                                <i className="ico-star active"></i>
                              </div>
                            </div>
                            <p>
                              To provide a feedback about the seller, you must
                              buy this product on $10
                            </p>
                          </div>
                          <div className="rightSide">
                            <button data-hystmodal="#addReview">
                              Write a review
                            </button>
                          </div>
                        </div>
                      </section>
                      <section id="comments">
                        <div className="addComment__wrapper"></div>
                        <div className="comments__wrapper">
                          <div className="comments__list">
                            {comments.map((data) => (
                              <CommentItem key={uuidv4()} {...data} />
                            ))}
                          </div>
                        </div>
                      </section>
                    </div>
                  </div>
                </div>
              </section>
            </div>
            <div className="sideData">
              <div className="order__dataWrapper">
                <form action="" method="">
                  <div className="selectPlan__wrapper">
                    <label className="popular">
                      <input
                        type="radio"
                        name="tariff"
                        value="7"
                        data-qty="1"
                        data-price="5"
                      />
                      <div className="top">
                        <span className="value">50</span>
                        <span className="ed">pc</span>
                        <span className="additional">
                          / <span>5$</span>
                        </span>
                      </div>
                      <div className="bottom">
                        <span className="complex">
                          For every <span className="under">10 pc</span> you
                          lose <span className="under">$15</span>
                        </span>
                      </div>
                      <span className="tag">Popular</span>
                    </label>
                    <label>
                      <input
                        type="radio"
                        name="tariff"
                        value="7"
                        data-qty="1"
                      />
                      <div className="top">
                        <span className="value">1</span>
                        <span className="ed">pc</span>
                      </div>
                      <div className="bottom">
                        <span className="value">7</span>
                        <span className="currency">$</span>
                      </div>
                    </label>
                    <label>
                      <input
                        type="radio"
                        name="tariff"
                        value="7"
                        data-qty="2"
                      />
                      <div className="top">
                        <span className="value">1</span>
                        <span className="ed">pc</span>
                      </div>
                      <div className="bottom">
                        <span className="value">7</span>
                        <span className="currency">$</span>
                      </div>
                    </label>
                    <label>
                      <input
                        type="radio"
                        name="tariff"
                        value="7"
                        data-qty="3"
                      />
                      <div className="top">
                        <span className="value">1</span>
                        <span className="ed">pc</span>
                      </div>
                      <div className="bottom">
                        <span className="value">7</span>
                        <span className="currency">$</span>
                      </div>
                    </label>
                    <label>
                      <input
                        type="radio"
                        name="tariff"
                        value="7"
                        data-qty="10"
                      />
                      <div className="top">
                        <span className="value">1</span>
                        <span className="ed">pc</span>
                      </div>
                      <div className="bottom">
                        <span className="value">7</span>
                        <span className="currency">$</span>
                      </div>
                    </label>
                    <label>
                      <input
                        type="radio"
                        name="tariff"
                        value="7"
                        data-qty="15"
                      />
                      <div className="top">
                        <span className="value">1</span>
                        <span className="ed">pc</span>
                      </div>
                      <div className="bottom">
                        <span className="value">7</span>
                        <span className="currency">$</span>
                      </div>
                    </label>
                    <label>
                      <input
                        type="radio"
                        name="tariff"
                        value="7"
                        data-qty="20"
                      />
                      <div className="top">
                        <span className="value">1</span>
                        <span className="ed">pc</span>
                      </div>
                      <div className="bottom">
                        <span className="value">12</span>
                        <span className="currency">$</span>
                      </div>
                    </label>
                  </div>
                  <div className="country__choose"></div>
                  <div className="order__counter">
                    <div className="counter">
                      <button type="button">-</button>
                      <input type="text" placeholder="1" />
                      <button type="button">+</button>
                    </div>
                    <div className="item__price">
                      <span className="value">0,00</span>
                      <span className="currency">$</span>
                    </div>
                  </div>
                  <div className="item__data">
                    <span className="left">
                      Only <span className="value">120</span> pieces left
                    </span>
                    <span className="soldout">
                      <span className="value">Sold ~ 12000</span> pieces per
                      month
                    </span>
                  </div>
                  <div className="action__area">
                    <button type="submit">
                      Add to <i className="ico-cart"></i>
                    </button>
                    <button type="button">Buy 1 click</button>
                  </div>
                </form>
              </div>
              <div className="sellers__wrapper">
                <a href="" title="">
                  <div className="left__side">
                    <img src="/img/tests/ava.png" alt="" />
                    <div className="content">
                      <span className="title">All sellers</span>
                      <span className="subtext">From $0,30</span>
                    </div>
                  </div>
                  <div className="right__side">
                    <div className="count__value">6</div>
                    <i className="ico-arrow"></i>
                  </div>
                </a>
              </div>
            </div>
          </div>
        </main>
        <Footer />
        <Scripts />
      </div>
    </div>
  );
}
