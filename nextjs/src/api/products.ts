import { AxiosResponse } from "axios";
import snakecaseKeys from "snakecase-keys";
import api from "./";
import type {
  IBaseQueryParams,
  IGetProductsQueryParams,
  IGetProductsFeaturedQueryParams,
  IGetProductsSearchQueryParams,
  IGetProductsCategoryQueryParams,
  IGetProductAvailabilityQueryParams,
  IGetProductRecommendationsQueryParams
} from "@/types/request";
import type { IGetProductsCategoryResponse, IGetProductsResponse, IGetProductsStatsResponse } from "@/types/response";
import { IProductAvailability, IProxyProduct, IProductCountryInfo } from "@/types/data";

interface QueryParams {
  getAll: IGetProductsQueryParams;
  getFeatured: IGetProductsFeaturedQueryParams;
  getSearch: IGetProductsSearchQueryParams;
  getCategory: IGetProductsCategoryQueryParams;
  getProductAvailability: IGetProductAvailabilityQueryParams;
  getProductRecommendations: IGetProductRecommendationsQueryParams;
}

export class ProductsAPI {
  static defaultQueryParams: QueryParams = {
    getAll: { page: 1, perPage: 20, sort: "created_at_desc", inStockOnly: false, featuredOnly: false },
    getFeatured: { limit: 5 },
    getSearch: { q: "", skip: 0, limit: 20 },
    getCategory: { page: 1, perPage: 20 },
    getProductAvailability: { quantity: 1 },
    getProductRecommendations: { limit: 5 }
  }

  static async get(productId: number): Promise<AxiosResponse<IProxyProduct>> {
    return await api.get(`/products/${productId}`);
  }

  static async getAll(params: IGetProductsQueryParams = ProductsAPI.defaultQueryParams.getAll): Promise<AxiosResponse<IGetProductsResponse>> {
    const searchParams = new URLSearchParams(
      snakecaseKeys(params as unknown as Record<string, string>)
    );
    return await api.get(`/products?${searchParams.toString()}`);

  }

  static async getStats(): Promise<AxiosResponse<IGetProductsStatsResponse>> {
    return await api.get(`/products/stats`);
  }

  static async getFeatured(params: IGetProductsFeaturedQueryParams = ProductsAPI.defaultQueryParams.getFeatured): Promise<AxiosResponse<IProxyProduct[]>> {
    const searchParams = new URLSearchParams(
      snakecaseKeys(params as unknown as Record<string, string>)
    );
    return await api.get(`/products/featured/?${searchParams.toString()}`);
  }

  static async getSearch(params: IGetProductsSearchQueryParams = ProductsAPI.defaultQueryParams.getSearch): Promise<AxiosResponse<IProxyProduct[]>> {
    const searchParams = new URLSearchParams(
      snakecaseKeys(params as unknown as Record<string, string>)
    );
    return await api.get(`/products/featured/?${searchParams.toString()}`);
  }

  static async getCategory(category: number, params: IGetProductsCategoryQueryParams = ProductsAPI.defaultQueryParams.getCategory): Promise<AxiosResponse<IGetProductsCategoryResponse>> {
    const searchParams = new URLSearchParams(
      snakecaseKeys(params as unknown as Record<string, string>)
    );
    return await api.get(`/products/categories/${category}?${searchParams.toString()}`);
  }

  static async getCategoriesStats(): Promise<AxiosResponse<IGetProductsStatsResponse>> {
    return await api.get(`/products/categories/stats`);
  }

  static async getCountries(): Promise<AxiosResponse<IProductCountryInfo[]>> {
    return await api.get(`/products/countries`);
  }

  static async getProductAvailability(productId: number, params: IGetProductAvailabilityQueryParams = ProductsAPI.defaultQueryParams.getProductAvailability): Promise<AxiosResponse<IProductAvailability>> {
    const searchParams = new URLSearchParams(
      snakecaseKeys(params as unknown as Record<string, string>)
    );
    return await api.get(`/products/${productId}/availability?${searchParams.toString()}`);
  }

  static async getProductRecommendations(productId: number, params: IGetProductRecommendationsQueryParams = ProductsAPI.defaultQueryParams.getProductRecommendations): Promise<AxiosResponse<IProxyProduct[]>> {
    const searchParams = new URLSearchParams(
      snakecaseKeys(params as unknown as Record<string, string>)
    );
    return await api.get(`/products/${productId}/recommendations?${searchParams.toString()}`);
  }
}
