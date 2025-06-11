import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { IProxyProduct, ISellerProduct } from "@/types/data";
import type { IBaseError } from "@/types/error";

interface IPurchaseStore {
  isLoading: boolean;
  isError: boolean;
  error: IBaseError | null;
  purchaseList: Array<ISellerProduct & IProxyProduct>;
  setPurchaseList: (purchaseList: Array<ISellerProduct & IProxyProduct>) => void;
  updatePurchaseList: (newPurchaseList: Array<ISellerProduct & IProxyProduct>) => void;
  // postPurchaseList: (list: IProxyProduct[]) => Promise<void>;
}

export const usePurchaseStore = create<IPurchaseStore>()(
  persist(
    (set) => ({
      isLoading: false,
      isError: false,
      error: null,
      purchaseList: [],
      setPurchaseList: (purchaseList) => set({ purchaseList }),
      updatePurchaseList: (newPurchaseList) => {
        set((state) => {
          const idList = state.purchaseList.map((item) => item.id);
          return {
            purchaseList: [
              ...state.purchaseList,
              ...newPurchaseList.filter((item) => !idList.includes(item.id))
            ]
          };
        })
      }
    }),
    {
      name: "gemups-purchase-storage",
    }
  )
);
