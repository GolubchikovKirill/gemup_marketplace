import { create } from "zustand";
import { persist } from "zustand/middleware";
import axios from "axios";
import type { IProxyProduct, ISellerProduct } from "@/types/data";
import type { IBaseError } from "@/types/error";

interface IProductStore {
  isLoading: boolean;
  isError: boolean;
  error: IBaseError | null;
  productList: Array<ISellerProduct & IProxyProduct>;
  setProductList: (productList: Array<ISellerProduct & IProxyProduct>) => void;
  getProductList: (skipProductList?: Array<ISellerProduct & IProxyProduct>) => Promise<void>;
  deleteProductList: (productList: Array<ISellerProduct & IProxyProduct>) => Promise<void>;
  deleteProductListItem: (productId: number) => Promise<void>;
}

export const useProductStore = create<IProductStore>()(
  persist(
    (set) => ({
      isLoading: false,
      isError: false,
      error: null,
      productList: [],
      setProductList: (productList) => set({ productList }),
      getProductList: async (skipProductList = []) => {
        const response = await axios.get("http://127.0.0.1:3000/api/proxy");
        if ([200, 201].includes(response.status)) {
          const uniqueItemsData: Record<string, any> = {};
          const arr = [...response.data.data, ...skipProductList];

          for (const item of arr) {
            uniqueItemsData[item.id] = item;
          }

          set({ productList: Object.values(uniqueItemsData) });
        }
      },
      deleteProductList: async (productList) => {
        const idList = productList.map((item) => item.id);
        set((state) => ({
          productList: state.productList.filter((item) => !idList.includes(item.id))
        }));
      },
      deleteProductListItem: async (productId) => {
        set((state) => ({
          productList: state.productList.filter((item) => item.id !== productId),
        }));
      },
    }),
    {
      name: "gemups-product-storage",
    }
  )
);
