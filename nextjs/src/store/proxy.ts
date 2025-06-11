import { create } from "zustand";
import { persist } from "zustand/middleware";
import axios from "axios";
import { TTL } from "@/constants";
import type {
  IProxyBaseData,
  IProxyProviderData,
  IProxySettings,
  ProxyFormatType,
  ProxyLocationType,
  ProxyProtocolType,
  ProxySessionType,
} from "@/types/data";
import type { IBaseError } from "@/types/error";

interface IProxySettingsStore extends IProxySettings {
  
}

interface IProxyListStore {
  isLoading: boolean;
  isError: boolean;
  error: IBaseError | null;
  proxyList: IProxyBaseData[];
  setProxyList: (proxyList: IProxyBaseData[]) => void;
  getProxyList: (proxySettings?: IProxySettings) => Promise<void>
}

export const useProxySettingsStore = create<IProxySettingsStore>()(
  persist(
    (set) => ({
      providerList: [],
      protocol: "HTTPS",
      count: 100,
      format: "ip:port:login:password",
      locationType: "Random",
      country: "",
      state: "",
      city: "",
      sessionType: "Dynamic",
      ttl: "60 min",
      setValue: <K extends keyof Omit<IProxySettingsStore, "setValue">>(
        key: K,
        value: IProxySettingsStore[K]
      ) => {
        set((state) => ({
          ...state,
          [key]: value,
        }));
      },
    }),
    {
      name: "gemups-proxy-settings-store",
    }
  )
);


export const useProxyListStore = create<IProxyListStore>()(
  persist(
    (set) => ({
      isLoading: false,
      isError: false,
      error: null,
      proxyList: [],
      setProxyList: (proxyList) => set({ proxyList }),
      getProxyList: async (proxySettings) => {
        let url = "http://127.0.0.1:3000/api/proxyList";
        if (proxySettings) {
          const onlyValidProxySettings: Record<string, any> = {};
          for (const [key, value] of Object.entries(proxySettings)) {
            if (
              !["function", "object", "symbol"].includes(typeof(key)) &&
              !["function", "object", "symbol"].includes(typeof(value))
            ) {
              onlyValidProxySettings[key] = value;
            }
          }

          const searchParams = new URLSearchParams(onlyValidProxySettings as unknown as Record<string, string>)
          url = `${url}?${searchParams.toString()}`;
        }

        const response = await axios.get(url);
        if ([200, 201].includes(response.status)) {
          set((state) => {
            const proxyListData: Record<string, IProxyBaseData> = {};
            const proxyList = response.data.data as IProxyBaseData[];
            const allProxyList = [...state.proxyList, ...proxyList];

            for (const proxy of allProxyList) {
              proxyListData[`${proxy.ip}_${proxy.port}`] = proxy;
            }

            return { proxyList: Object.values(proxyListData) };
          });
        }
      }
    }),
    {
      name: "gemups-proxy-list-store",
    }
  )
);
