import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { IProxyProduct } from "@/types/data";
import type { IBaseError } from "@/types/error";


interface IProfileStore {
    isLoading: boolean;
    isError: boolean;
    error: IBaseError | null;
    offerList: IProxyProduct[];
    setOfferList: (offerList: IProxyProduct[]) => void;
    updateOfferList: (offerList: IProxyProduct[]) => Promise<void>;
}