import { TTL } from "@/constants";

export type LanguageType = "EN" | "RU" | "KZ" | "FR";
export type CurrencyCodeType = "USD" | "EUR";
export type ProxyProtocolType = "HTTP" | "HTTPS" | "SOCKS5";
export type ProxySessionType = "Dynamic" | "Static";
export type ProxyLocationType = "Random" | "Country";
export type ProxyFormatType =
  | "ip:port:login:password"
  | "ip:port@login:password"
  | "login:password@ip:port"
  | "login:password:ip:port";

export interface IAppSettings {
  language: LanguageType;
  isSidebarOpen: boolean;
  isMenuOpen: boolean;
}

export interface IUserBaseInfo {
  email: string;
  username: string;
  firstName: string;
  lastName: string;
}

export interface IUserBalanceInfo {
  balance: string;
  currency: string;
  userId: number;
  isGuest: boolean;
  formattedBalance: string;
  lastUpdated: string;
  pendingTopups: string;
  totalDeposited: string;
}

export interface IUserStats {
  totalOrders: number;
  totalSpent: string;
  activeProxies: number;
  lastOrderDate: string;
  registrationDate: string;
  daysSinceRegistration: number;
  averageOrderAmount: string;
  totalProxiesPurchased: number;
  periodDays: number;
  currency: string;
}

export interface IUser extends IUserBaseInfo {
  id: number;
  isActive: boolean;
  isVerified: boolean;
  isGuest: boolean;
  isAdmin: boolean;
  role: string;
  balance: string;
  guestSessionId: string;
  createdAt: string;
  updatedAt: string;
}

export interface ITopupBalance {
  amount: number;
  paymentMethod: "cryptomus" | string;
  currency: CurrencyCodeType;
}

export interface ISellerProduct {
  id: string;
  tags: string[];
  imgSrc: string;
  rating: number;
  shop: string;
  sellerList: Array<{
    avatar: string;
  }>;
  product: {
    name: string;
    count: number;
    description: string;
  };
  price: number;
  currency: string;
  progress: number;
}

export interface IProxySettings {
  providerList: IProxyProviderData[];
  protocol: ProxyProtocolType;
  count: number;
  format: ProxyFormatType;
  locationType: ProxyLocationType;
  country: string;
  state: string;
  city: string;
  sessionType: ProxySessionType;
  ttl: keyof typeof TTL;
}

export interface IProxyProviderData {
  id: string | number;
  isActive: boolean;
  icon?: string;
  name: string;
  tag?: string;
}

export interface IProxyBaseData {
  type: ProxyProtocolType;
  ip: string;
  port: number;
  login: string;
  password: string;
}

export interface IProxyProductOld extends ISellerProduct {
  type: "Residential" | "Datacenter" | string;
}

export interface IPurchase {
  id: string;
  active: boolean;
  name: string;
  category: string;
  shop: string;
}

export interface IProxyProduct {
  id: number;
  name: string;
  description: string;
  proxyType: "http" | "socks5" | string;
  proxyCategory: string;
  sessionType: "sticky" | string;
  countryCode: string;
  countryName: string;
  city: string;
  pricePerProxy: string;
  durationDays: number;
  minQuantity: number;
  maxQuantity: number;
  stockAvailable: number;
  maxThreads: number;
  speedMbps: number;
  uptimeGuarantee: string;
  isFeatured: boolean;
}

export interface ICartItem {
  id: number;
  userId: number;
  guestSessionId: string;
  proxyProductId: number;
  quantity: number;
  generationParams: string;
  expiresAt: string;
  createdAt: string;
  updatedAt: string;
  proxyProduct: IProxyProduct;
  unitPrice: string;
  totalPrice: string;
  isAvailable: boolean;
  stockStatus: "in_stock" | string;
}

export interface ICartSummary {
  totalItems: number;
  totalAmount: string;
  currency: string;
  itemsCount: number;
  userType: "guest" | string;
  estimatedDelivery: string;
  hasNodepayProducts: boolean;
  hasProxyProducts: boolean;
  hasUnavailableItems: boolean;
  categoriesBreakdown: Record<string, number>;
  countriesBreakdown: Record<string, number>;
}

export interface ICartData {
  items: ICartItem[];
  summary: ICartSummary;
  lastUpdated: string;
  expiresAt: string;
  isGuest: boolean;
}

export interface IProductsCategoryStats {
  category: string;
  categoryName: string;
  productsCount: number;
  avgPrice: string;
  countriesCount: number;
  minPrice: string;
  maxPrice: string;
}

export interface IProductsCountries {
  countryCode: string;
  countryName: string;
  productsCount: number;
  flagUrl: string;
  avgPrice: string;
  categories: string[];
}

export interface IProductAvailability {
  productId: number;
  requestedQuantity: number;
  availableQuantity: number;
  isAvailable: boolean;
  estimatedPrice: string;
  currency: CurrencyCodeType;
  message: string;
  stockAvailable: number;
  maxQuantity: number;
  pricePerUnit: string;
  totalPrice: string;
}

export interface IProductCountryInfo {
  countryCode: string;
  countryName: string;
  productsCount: number;
  flagUrl: string;
  avgPrice: string;
  categories: string[];
}
