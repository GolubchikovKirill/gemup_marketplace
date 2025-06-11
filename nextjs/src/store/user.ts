import { create } from "zustand";
import { persist } from "zustand/middleware";
import camelcaseKeys from "camelcase-keys";
import api from "@/api";
import { IUser, IUserBaseInfo, ITopupBalance } from "@/types/data";
import { IBaseError } from "@/types/error";
import { UserAPI } from "@/api/user";

interface IUserStore {
  isLoading: boolean;
  isError: boolean;
  error: IBaseError | null;
  user: IUser | null;
  setUser: (user: IUser) => void;
  getUser: () => Promise<void>;
  //   updateUser: (data: IUserInfo) => Promise<void>
  //   deleteUser: () => Promise<void>
  //   getUserBalance: () => Promise<void>
  //   postTopupBalance: (data: ITopupBalance) => Promise<void>
}

export const useUserStore = create<IUserStore>()(
  persist(
    (set) => ({
      isLoading: false,
      isError: false,
      error: null,
      user: null,
      setUser: (user) => set({ user }),
      getUser: async () => {
        try {
          const response = await UserAPI.get();
          const data = response.data;

          if ([200, 201].includes(response.status)) {
            set({ user: data });
          } else {
            // @ts-ignore
            set({ isLoading: false, isError: true, error: data });
          }
        } catch (e) {
          // @ts-ignore
          set({ isLoading: false, isError: true, error: e?.response?.data });
        }
      },
    }),
    {
      name: "gemups-user-store"
    }
  )
);
