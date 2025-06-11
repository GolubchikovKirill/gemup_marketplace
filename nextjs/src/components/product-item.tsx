"use client"

import { useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import { IProxyProduct, ISellerProduct } from "@/types/data";
import { useCartStore } from "@/store/cart";
import Link from "next/link";


type Props = ISellerProduct & IProxyProduct;


// id: uuidv4(),
//     tags: ["Confirmed by mail", "Tdata", "Europe"],
//     imgSrc: "/img/tests/product.png",
//     rating: 5,
//     shop: "NVS Shop",
//     sellerList: [
//       { avatar: "/img/tests/ava.png" },
//       { avatar: "/img/tests/ava.png" },
//       { avatar: "/img/tests/ava.png" },
//       { avatar: "/img/tests/ava.png" },
//       { avatar: "/img/tests/ava.png" }
//     ],
//     product: {
//       name: "Twitter accounts | 2FA | Avatar added | First tweet made | Verified by email (included)",
//       count: 120,
//       description: "Unlimited IPs + Sessions. Pay only for gb.",
//     },
//     price: 0.30,
//     currency: "$",
//     progress: 75

export const ProductItem: React.FC<Props> = ({
  id = 0,
  name = "",
  description = "",
  pricePerProxy = "0",
  minQuantity = 0,
  tags = ["Confirmed by mail", "Tdata", "Europe"],
  imgSrc = "/img/tests/product.png",
  rating = 5,
  shop = "NVS Shop",
  sellerList = [
      { avatar: "/img/tests/ava.png" },
      { avatar: "/img/tests/ava.png" },
      { avatar: "/img/tests/ava.png" },
      { avatar: "/img/tests/ava.png" },
      { avatar: "/img/tests/ava.png" }
    ],
  currency = "$",
  progress = 75,
}) => {
  const { data, postItem } = useCartStore((state) => state);
  
  return (
    <div className="product__item">
      <div className="product">
        <div className="product__wrapper">
          <div className="product__tags">
            <span className="tag icon">
              <i className="ico-shield"></i>
            </span>
            {tags.map((tag) => (
              <span key={uuidv4()} className="tag">
                {tag}
              </span>
            ))}
          </div>
          <div className="product__data">
            <div className="product__img">
              <img src="/img/tests/product.png" alt="name" />
            </div>
            <div className="data__wrapper">
              <div className="left__side">
                <div className="rating__wrapper">
                  <i className="ico-star"></i>
                  <span className="rating">{rating}</span>
                </div>
                <span className="name">{shop}</span>
              </div>
              <div className="right__side">
                <div className="avatars__wrapper">
                  {sellerList.length > 3
                    ? sellerList
                        .slice(0, 3)
                        .map(({ avatar }) => (
                          <img key={uuidv4()} src={avatar} alt="name" />
                        ))
                    : sellerList.map(({ avatar }) => (
                        <img key={uuidv4()} src={avatar} alt="name" />
                      ))}
                </div>
                <span className="seller">{sellerList.length}</span>
              </div>
            </div>
            <div className="content__area">
              <Link className="name" href={`/accounts/${id}`}>{name}</Link>
              <div className="sub__content">
                <p>{description}</p>
              </div>
              <button className="openContent">
                <i className="ico-arrow"></i>
              </button>
            </div>
          </div>
          <div className="buttom">
            <div className="price">
              <span className="currency">{currency}</span>
              <span className="value">{pricePerProxy}</span>
            </div>
            <div className="itemsLeft">
              <span className="desk">
                Only <span>{minQuantity}</span> pieces left
              </span>
              <div className="progress-bar">
                <div className="remaining"></div>
                <span className="value">{progress}%</span>
              </div>
            </div>
            <div className="order__action">
              <button onClick={() => postItem(id, 1, "")}>
                <i className="ico-cart"></i>
              </button>
              <div className="order__counter">
                <form action="">
                  <button>-</button>
                  <input type="text" placeholder="1" />
                  <button>+</button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
