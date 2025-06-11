import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { v4 as uuidv4 } from "uuid";


export function middleware(request: NextRequest) {
  const response = NextResponse.next();

  const accessToken = request.cookies.get("access_token")?.value;
  const sessionId = request.cookies.get("session_id")?.value;
  const { pathname } = request.nextUrl;

  const routes = {
    auth: ["/login", "/register"],
    onlyAuth: ["/profile"]
  }

  if (!accessToken && !sessionId) {
    response.cookies.set("session_id", uuidv4());
  }

  // if (accessToken && routes.auth.includes(pathname)) {
  //   return NextResponse.redirect(new URL("/", request.url));
  // }

  // if (!accessToken && !routes.auth.includes(pathname)) {
  //   return NextResponse.redirect(new URL("/login", request.url));
  // }

  return response;
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|.*\\.(?:png|jpg|jpeg|svg|webp|ico|css|js|woff2?)$).*)'
  ],
};
