import type { IProxyBaseData, ProxyFormatType, ProxyProtocolType } from "@/types/data";

export const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export function calculateDateByDays(
  daysDifference: number,
  operator: "+" | "-" = "+"
) {
  const today = new Date();

  const date = new Date(today);
  date.setDate(
    operator === "+"
      ? today.getDate() + daysDifference
      : today.getDate() - daysDifference
  );

  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();

  return `${day}.${month}.${year}`;
}

export function getProxyStr(proxy: IProxyBaseData, format: ProxyFormatType) {
  const { type, ip, port, login, password } = proxy;
  
  switch (format) {
    case "ip:port:login:password":
      return `${type.toLowerCase()}://${ip}:${port}:${login}:${password}`;
    case "ip:port@login:password":
      return `${type.toLowerCase()}://${ip}:${port}@${login}:${password}`;
    case "login:password:ip:port":
      return `${type.toLowerCase()}://${login}:${password}:${ip}:${port}`;
    case "login:password@ip:port":
      return `${type.toLowerCase()}://${login}:${password}@${ip}:${port}`;
  }
};

export function generateRandomProxy(protocol?: ProxyProtocolType): IProxyBaseData {
  const types: ProxyProtocolType[] = ["HTTP", "HTTPS", "SOCKS5"];
  const type = protocol || types[Math.floor(Math.random() * types.length)];
  const ip = Array(4).fill(0).map(() => Math.floor(Math.random() * 256)).join('.');
  const port = Math.floor(Math.random() * (65535 - 1024 + 1)) + 1024;

  const generateRandomString = (length: number) => {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return result;
  };

  const login = generateRandomString(8);
  const password = generateRandomString(12);

  return {
    type,
    ip,
    port,
    login,
    password,
  };
}