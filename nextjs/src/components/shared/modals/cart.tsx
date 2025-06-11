"use client";

import { useEffect, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { useCartStore } from "@/store/cart";
import { InputPlacetop } from "../forms/input-placetop";
import { CURRENCY } from "@/constants";
import { usePurchaseStore } from "@/store/purchase";
import { useProductStore } from "@/store/product";
import { IProxyProduct, ISellerProduct } from "@/types/data";

interface Props {}

export const CartModal: React.FC<Props> = () => {
  const [totalPrice, setTotalPrice] = useState<string | number>(0);
  const [currency, setCurrency] = useState<string>("");
  const { isOpen, isValid, isLoading, isError, data, setIsOpen, setData, getData, updateItem, deleteItem } = useCartStore((state) => state);
  const { productList, setProductList, deleteProductList } = useProductStore((state) => state);
  const { purchaseList, setPurchaseList, updatePurchaseList } = usePurchaseStore((state) => state);


  useEffect(() => {
    if (data) {
      const key = data.summary.currency.toLowerCase() as keyof typeof CURRENCY;
      setCurrency(CURRENCY[key]);
      setTotalPrice(data.summary.totalAmount);
    }
  }, [data]);

  const updateCartItem = async (
    itemId: number,
    currentQuantity: number,
    generationParams: string,
    operator: "+" | "-"
  ) => {
    if (currentQuantity - 1 < 0 && operator === "-") {
      return;
    }

    switch (operator) {
      case "+":
        await updateItem(itemId, currentQuantity + 1, generationParams);
        break;
      case "-":
        await updateItem(itemId, currentQuantity - 1, generationParams);
        break;
      default:
        break;
    }
  };

  const handleOrder = async () => {
    if (data?.items && data?.items.length > 0) {
      const proxyProductList = data.items.map((item) => item.proxyProduct);

      deleteProductList(proxyProductList as Array<ISellerProduct & IProxyProduct>);
      updatePurchaseList(proxyProductList as Array<ISellerProduct & IProxyProduct>);
      setData(null);
    }
  };
  
  const calculateTotalPrice = () => {
    let totalPrice = 0;
    if (data?.items && data?.items.length > 0) {
      data.items.forEach(
        (item) => (totalPrice += +item.proxyProduct.pricePerProxy * item.quantity)
      );
    }

    return totalPrice;
  };

  const handleQuantityChange = async (e: React.ChangeEvent<HTMLInputElement>, id: number, generationParams: string) => {
    const quantity = parseInt(e.target.value);
    if (!Number.isNaN(quantity)) {
      await updateItem(id, quantity, generationParams);
    }
  }

  return (
    <div className={`hystmodal ${isOpen ? "hystmodal__opened hystmodal--active" : ""}`} id="cartModal">
      <div className="hystmodal__wrap">
        <div
          className="hystmodal__window baseModal"
          role="dialog"
          aria-modal="true"
        >
          <span data-hystclose className="ico-close" onClick={() => setIsOpen(false)}></span>
          <div className="form__data">
            <div className="form__header">
              <p className="title">
                Cart <span className="value">{}</span>
              </p>
            </div>
            <div className="cart__inner">
              {data?.items && data?.items.length > 0 ? (
                <div className="cartProducts__wrapper">
                  {data?.items?.length > 0 && data?.items.map(
                    ({
                      id,
                      quantity,
                      generationParams,
                      proxyProduct: {
                        name,
                        description,
                        proxyCategory,
                        pricePerProxy,
                      },
                    }) => (
                      <div className="cart__item" key={id}>
                        <div className="ava__wrapper">
                          <img src="/img/tests/ava.png" alt="name" />
                        </div>
                        <div className="product__data">
                          <div className="top__data">
                            <span className="service">{proxyCategory}</span>
                            <span className="shop">{"shop"}</span>
                          </div>
                          <a className="prodName" href="#">
                            {name}
                          </a>
                          <div className="bottom__area">
                            <div className="order__counter">
                              <button
                                type="button"
                                onClick={() => updateCartItem(id, quantity, generationParams, "-")}
                              >
                                -
                              </button>
                              <input
                                type="text"
                                placeholder="1"
                                value={quantity}
                                onChange={(e) => handleQuantityChange(e, id, generationParams)}
                              />
                              <button
                                type="button"
                                onClick={() => updateCartItem(id, quantity, generationParams, "+")}
                              >
                                +
                              </button>
                            </div>
                            <div className="price">
                              <span className="value">{parseFloat(String(+pricePerProxy * quantity)).toFixed(2)}</span>
                              <span className="currency">{currency}</span>
                            </div>
                            <button className="deleteProd" onClick={() => deleteItem(id)}>
                              <i className="ico-delete"></i>
                            </button>
                          </div>
                        </div>
                      </div>
                    )
                  )}
                </div>
              ) : (
                <div className="cart__noitems">
                  <i className="ico-cart-bag decor"></i>
                  <div className="text__data">
                    <span className="title">You have no products</span>
                    <span className="subtext">
                      Add your first product and you will be able to view and
                      buy it
                    </span>
                  </div>
                  <a className="noitems" href="#">
                    <i className="ico-plus"></i> Add Offer
                  </a>
                </div>
              )}
            </div>
            <div className="bottom__actions">
              <InputPlacetop
                id="promocode"
                type="text"
                name="promocode"
                placeholder=""
                label="Add promocode"
              />
              <div className="order__data">
                <div className="price__wrapper">
                  <span className="label">For Payment</span>
                  <div className="price__data">
                    <span className="currency">{currency}</span>
                    <span className="value">{calculateTotalPrice().toFixed(2)}</span>
                  </div>
                </div>
                <button className="make__order" onClick={handleOrder}>Place an order</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
