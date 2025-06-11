import { IUserBaseInfo } from "./data";

export interface IBaseQueryParams {
  page: number;
  perPage: number;
  skip: number;
  limit: number;
}

export interface IGetProductsQueryParams
  extends Pick<IBaseQueryParams, "page" | "perPage"> {
  search?: string;
  proxyCategory?: string;
  proxyType?: string;
  provider?: string;
  countryCode?: string;
  minPrice?: number;
  maxPrice?: number;
  sort: "created_at_asc" | "created_at_desc" | string;
  inStockOnly: boolean;
  featuredOnly: boolean;
}

export interface IGetProductsFeaturedQueryParams
  extends Pick<IBaseQueryParams, "limit"> {
  category?: string;
}

export interface IGetProductsSearchQueryParams
  extends Pick<IBaseQueryParams, "skip" | "limit"> {
  q: string;
}

export interface IGetProductsCategoryQueryParams
  extends Pick<IBaseQueryParams, "page" | "perPage"> {}

export interface IGetProductAvailabilityQueryParams {
  quantity: number;
}

export interface IGetProductRecommendationsQueryParams
  extends Pick<IBaseQueryParams, "limit"> {}

export interface IGetUserStatsQueryParams {
  days: number
}

export interface IGetUsersSearchQueryParams extends Pick<IBaseQueryParams, "skip" | "limit"> {
  query: string;
}

export interface IUpdateUserRequestBody extends IUserBaseInfo {}

export interface IPostCartItemsRequestBody {
  proxyProductId: number;
  quantity: number;
  generationParams: string;
}
