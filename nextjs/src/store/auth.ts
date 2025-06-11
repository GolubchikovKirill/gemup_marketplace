import { create } from "zustand";
import camelcaseKeys from "camelcase-keys";
import Cookies from "js-cookie";
import api from "@/api";
import type { IUser } from "@/types/data";
import type { IAuthTokenData } from "@/types/auth";
import type { IAuthError } from "@/types/error";
import { persist } from "zustand/middleware";

interface IAuthStore {
  isAuth: boolean;
  isLoading: boolean;
  isError: boolean;
  error: IAuthError | null;
  user: IUser | null;
  setLoading: (isLoading: boolean) => void
  setError: (isError: boolean, error: IAuthError | null) => void
  setUser: (user: IUser) => void;
  register: (
    username: string,
    email: string,
    password: string,
    referralCode?: string
  ) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<IAuthStore>()(
  persist(
    (set) => ({
      isAuth: false,
      isLoading: false,
      isError: false,
      error: null,
      user: null,
      setLoading: (isLoading) => set({ isLoading }),
      setError: (isError, error) => set({ isError, error }),
      setUser: (user) => set({ user }),
      register: async (username, email, password, referralCode) => {
        set({ isLoading: true, isError: false, error: null });

        try {
          const response = await api.post(
              `/auth/register`,
              { username, email, password }
          );
      
          if ([200, 201].includes(response.status)) {
            set({ user: camelcaseKeys(response.data) });
          } else {
            set({ isError: true, error: camelcaseKeys(response.data) });
          }
        } catch (e) {
          // @ts-ignore
          set({ isError: true, error: e?.response?.data ? camelcaseKeys(e?.response?.data) : null });
        }

        set({ isLoading: false });
      },
      login: async (email, password) => {
        set({ isLoading: true, isError: false, error: null });

        try {
          const response = await api.post(
              `/auth/login/json`,
              { email, password }
          );

          if ([200, 201].includes(response.status)) {
            const userData = camelcaseKeys(response.data) as IAuthTokenData & { user: IUser }
            Cookies.set("access_token", userData.accessToken, { expires: userData.expiresIn });
            Cookies.set("refresh_token", userData.refreshToken);
            set({ isAuth: true, user: camelcaseKeys(response.data?.user) });
          } else {
            set({ isError: true, error: camelcaseKeys(response.data) });
          }
        } catch (e) {
          // @ts-ignore
          set({ isError: true, error: e?.response?.data ? camelcaseKeys(e?.response?.data) : null });
        }

        set({ isLoading: false });
      },
      logout: async () => {
        set({ isLoading: true, isError: false, error: null });

        try {
          Cookies.remove("access_token");
          Cookies.remove("refresh_token");
          set({ isAuth: false, user: null });
          // const response = await api.post(
          //     `/auth/logout`,
          //     null,
          //     {
          //       headers: {
          //         Authorization: `Bearer ${Cookies.get("access_token")}`
          //       }
          //     }
          // );
          // const data = camelcaseKeys(response.data || {}, { deep: true });
      
          // if ([200, 201].includes(response.status)) {
          //   Cookies.remove("access_token");
          //   Cookies.remove("refresh_token");
          //   set({ isAuth: false, user: data?.user });
          // } else {
          //   set({ isError: true, error: data });
          // }
        } catch (e) {
          // @ts-ignore
          set({ isError: true, error: e?.response?.data ? camelcaseKeys(e?.response?.data) : null });
        }

        set({ isLoading: false });
      },
    }),
    {
      name: "gemups-auth-storage"
    }
  )
);