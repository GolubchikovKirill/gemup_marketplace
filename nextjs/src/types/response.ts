import { IProxyProduct, IUser } from "./data";

export interface IBaseGetResponse {
  total: number;
  page: number;
  perPage: number;
  pages: number;
}

export interface IBaseDeleteResponse {
  message: string;
  success: boolean;
  code: string;
  details: Record<string, string>;
}

export interface IGetProductsResponse
  extends Pick<IBaseGetResponse, "total" | "page" | "perPage" | "pages"> {
  items: IProxyProduct[];
}

export interface IGetProductsStatsResponse {
  totalProducts: number;
  activeProducts: number;
  featuredProducts: number;
  categoriesCount: number;
  countriesCount: number;
  providersCount: number;
  avgPrice: string;
  priceRange: Record<string, number>;
  totalStock: number;
  categoriesBreakdown: Record<string, number>;
  providersBreakdown: Record<string, number>;
}

export interface IGetProductsCategoryResponse
  extends Pick<IBaseGetResponse, "total" | "page" | "perPage"> {
  category: "datacenter" | string;
  categoryName: string;
  products: IProxyProduct[];
}

export interface IGetUsersSearchResponse extends IBaseGetResponse {
  users: IUser[]
}