import { create } from "zustand";
import { persist } from "zustand/middleware";
import axios from "axios";
import camelcaseKeys from "camelcase-keys";
import snakecaseKeys from "snakecase-keys";
import api from "@/api";
// import { proxyProducts } from "@/data";
import type { IBaseError } from "@/types/error";
import type { ICartItem, ICartSummary, ICartData, IProxyProduct, IProxyProductOld } from "@/types/data";

interface ICartStore {
  isOpen: boolean
  isValid: boolean | null;
  isLoading: boolean;
  isError: boolean;
  error: IBaseError | null;
  data: ICartData | null;
  summary: ICartSummary | null;
  setIsOpen: (isOpen: boolean) => void;
  setData: (data: ICartData | null) => void;
  setSummary: (summary: ICartSummary) => void;
  getSummary: () => Promise<void>;
  getData: () => Promise<void>;
  postItem: (
    proxyProductId: number,
    quantity: number,
    generationParams: string
  ) => Promise<void>;
  updateItem: (
    itemId: number,
    quantity: number,
    generationParams: string
  ) => Promise<void>;
  deleteItem: (itemId: number) => Promise<void>;
  deleteData: () => Promise<void>;
  validateData: () => Promise<void>;
}

export const useCartStore = create<ICartStore>()(
  persist(
    (set, get) => ({
      isOpen: false,
      isValid: null,
      isLoading: false,
      isError: false,
      error: null,
      data: null,
      summary: null,
      setIsOpen: (isOpen) => set({ isOpen }),
      setData: (data) => set({ data }),
      setSummary: (summary) => set({ summary }),
      getSummary: async () => {
        try {
          set({ isLoading: true });

          const response = await api.get("/cart/summary");
          const data = camelcaseKeys(response.data);

          if ([200, 201].includes(response.status)) {
            set({ summary: data });
          } else {
            set({ isLoading: false, isError: true, error: data });
          }
        } catch (e) {
          // @ts-ignore
          set({ isLoading: false, isError: true, error: e?.response?.data });
        }
      },
      getData: async () => {
        try {
          set({ isLoading: true });

          const response = await api.get("/cart");
          const data = camelcaseKeys(response.data);

          if ([200, 201].includes(response.status)) {
            set({ data });
          } else {
            set({ isLoading: false, isError: true, error: data });
          }
        } catch (e) {
          // @ts-ignore
          set({ isLoading: false, isError: true, error: e?.response?.data });
        }
      },
      postItem: async (proxyProductId, quantity, generationParams) => {
        const existData = get().data;
        if (existData && existData?.items?.length > 0) {
          const isItemExist = existData.items.find((item) => item.id === proxyProductId);
          if (isItemExist) {
            return;
          }
        }

        const response = await axios.get("http://127.0.0.1:3000/api/proxy");
        if ([200, 201].includes(response.status)) {
          const item = (response.data.data as IProxyProduct[]).find((item) => item.id === proxyProductId)
          if (item) {
            const cartItem: ICartItem = {
              proxyProduct: item,
              id: proxyProductId,
              userId: 0,
              guestSessionId: "",
              proxyProductId,
              quantity: 1,
              generationParams,
              expiresAt: "",
              createdAt: "",
              updatedAt: "",
              unitPrice: item.pricePerProxy,
              totalPrice: item.pricePerProxy,
              isAvailable: item.stockAvailable > 0,
              stockStatus: "in_stock"
            };

            set((state) => ({
              data: state.data
                ? {
                    ...state.data,
                    items: [...state.data.items, cartItem]
                  }
                : {
                  items: [cartItem],
                  summary: {
                    currency: "USD"
                  } as unknown as ICartSummary,
                  lastUpdated: "",
                  expiresAt: "",
                  isGuest: false,
                }
              }));
          }
        }
      },
      deleteItem: async (proxyProductId) => {
        set((state) => ({
          data: state.data
            ? { ...state.data, items: state.data.items.filter((item: ICartItem) => item.id !== proxyProductId) }
            : null
        }));
      },
      updateItem: async (proxyProductId, quantity, generationParams) => {
        set((state) => {
          if (state.data) {
            const itemIdx = state.data.items.findIndex((item) => item.id === proxyProductId);
            if (
              itemIdx >= 0 &&
              quantity <= state.data.items[itemIdx].proxyProduct.minQuantity
            ) {
              return {
                data: {
                  ...state.data,
                  items: [
                    ...state.data.items.slice(0, itemIdx),
                    { ...state.data.items[itemIdx], quantity, generationParams },
                    ...state.data.items.slice(itemIdx + 1)
                  ]
                }
              }
            }

            return {};
          } else {
            return {}
          }
        })
      },
      deleteData: async () => {
        set({ data: null, summary: null });
      },
      validateData: async () => {},
      // postItem: async (proxyProductId, quantity, generationParams) => {
      //   try {
      //     set({ isLoading: true });

      //     const response = await api.post(
      //       "/cart/items",
      //       snakecaseKeys({ proxyProductId, quantity, generationParams })
      //     );
      //     const data = camelcaseKeys(response.data);

      //     if ([200, 201].includes(response.status)) {
      //       set((state) => {
      //         if (state.data) {
      //           return {
      //             data: {
      //               ...state.data,
      //               items: [...state.data.items, data],
      //             },
      //           };
      //         } else {
      //           return { data: null };
      //         }
      //       });
      //     } else {
      //       set({ isLoading: false, isError: true, error: data });
      //     }
      //   } catch (e) {
      //     // @ts-ignore
      //     set({ isLoading: false, isError: true, error: e?.response?.data });
      //   }
      // },
      // updateItem: async (itemId, quantity, generationParams) => {
      //   try {
      //     set({ isLoading: true });

      //     const response = await api.put(
      //       `/cart/items/${itemId}`,
      //       snakecaseKeys({ quantity, generationParams })
      //     );
      //     const data = camelcaseKeys(response.data);

      //     if ([200, 201].includes(response.status)) {
      //       set((state) => {
      //         if (state.data) {
      //           const updatedItemIdx = state.data.items.findIndex(
      //             (item) => item.id === (data as ICartItem).id
      //           );
      //           return {
      //             data: {
      //               ...state.data,
      //               items: [
      //                 state.data.items.slice(0, updatedItemIdx),
      //                 data,
      //                 state.data.items.slice(updatedItemIdx + 1),
      //               ],
      //             },
      //           };
      //         } else {
      //           return { data: null };
      //         }
      //       });
      //     } else {
      //       set({ isLoading: false, isError: true, error: data });
      //     }
      //   } catch (e) {
      //     // @ts-ignore
      //     set({ isLoading: false, isError: true, error: e?.response?.data });
      //   }
      // },
      // deleteItem: async (itemId) => {
      //   try {
      //     set({ isLoading: true });

      //     const response = await api.delete(`/cart/items/${itemId}`);
      //     const data = camelcaseKeys(response.data);

      //     if ([200, 201].includes(response.status) && data?.success) {
      //       set((state) => {
      //         if (state.data) {
      //           return {
      //             data: {
      //               ...state.data,
      //               items: state.data.items.filter(
      //                 (item) => item.id !== itemId
      //               ),
      //             },
      //           };
      //         } else {
      //           return { data: null };
      //         }
      //       });
      //     } else {
      //       set({ isLoading: false, isError: true, error: data });
      //     }
      //   } catch (e) {
      //     // @ts-ignore
      //     set({ isLoading: false, isError: true, error: e?.response?.data });
      //   }
      // },
      // deleteData: async () => {
      //   try {
      //     set({ isLoading: true });

      //     const response = await api.delete("/cart");
      //     const data = camelcaseKeys(response.data);

      //     if ([200, 201].includes(response.status) && data?.success) {
      //       set({ data: null, summary: null });
      //     } else {
      //       set({ isLoading: false, isError: true, error: data });
      //     }
      //   } catch (e) {
      //     // @ts-ignore
      //     set({ isLoading: false, isError: true, error: e?.response?.data });
      //   }
      // },
      // validateData: async () => {
      //   try {
      //     set({ isLoading: true });

      //     const response = await api.delete("/cart");
      //     const data = camelcaseKeys(response.data);

      //     if ([200, 201].includes(response.status) && data?.success) {
      //       set({ isValid: true });
      //     } else {
      //       set({
      //         isValid: false,
      //         isLoading: false,
      //         isError: true,
      //         error: data,
      //       });
      //     }
      //   } catch (e) {
      //     set({
      //       isValid: false,
      //       isLoading: false,
      //       isError: true,
      //       // @ts-ignore
      //       error: e?.response?.data,
      //     });
      //   }
      // },
    }),
    {
      name: "gemups-cart-storage",
    }
  )
);
