import { AxiosResponse } from "axios";
import camelcaseKeys from "camelcase-keys";
import snakecaseKeys from "snakecase-keys";
import api from "./";
import type { IUser, IUserBalanceInfo, IUserStats } from "@/types/data";
import { IGetUsersSearchQueryParams, IGetUserStatsQueryParams, IUpdateUserRequestBody } from "@/types/request";
import type { IBaseDeleteResponse, IGetUsersSearchResponse } from "@/types/response";

interface QueryParams {
  getStats: IGetUserStatsQueryParams
  getUsersSearch: IGetUsersSearchQueryParams
}

export class UserAPI {
    static defaultQueryParams: QueryParams = {
        getStats: { days: 30 },
        getUsersSearch: { query: "", skip: 0, limit: 20 }
    }

    static async get(): Promise<AxiosResponse<IUser>> {
        const response = await api.get(`/users/me`);
        return { ...response, data: camelcaseKeys(response.data) };
    }

    static async update(payload: IUpdateUserRequestBody): Promise<AxiosResponse<IUser>> {
        const response = await api.put(`/users/me`, snakecaseKeys(payload as unknown as Record<string, string>));
        return { ...response, data: camelcaseKeys(response.data) };
    }

    static async delete(): Promise<AxiosResponse<IBaseDeleteResponse>> {
        const response = await api.get(`/users/me`);
        return { ...response, data: camelcaseKeys(response.data) };
    }

    static async getBalance(): Promise<AxiosResponse<IUserBalanceInfo>> {
        const response = await api.get(`/users/me`);
        return { ...response, data: camelcaseKeys(response.data) };
    }

    static async getStats(params: IGetUserStatsQueryParams = UserAPI.defaultQueryParams.getStats): Promise<AxiosResponse<IUserStats>> {
        const searchParams = new URLSearchParams(
            snakecaseKeys(params as unknown as Record<string, string>)
        );
        const response = await api.get(`/users/me`);
        return { ...response, data: camelcaseKeys(response.data) };
    }

    static async getUsersSearch(params: IGetUsersSearchQueryParams = UserAPI.defaultQueryParams.getUsersSearch): Promise<AxiosResponse<IGetUsersSearchResponse>> {
        const searchParams = new URLSearchParams(
            snakecaseKeys(params as unknown as Record<string, string>)
        );
        const response = await api.get(`/users/me`);
        return { ...response, data: camelcaseKeys(response.data) };
    }
}