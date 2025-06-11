import path from "path";
import { promises as fs } from "fs";
import { NextRequest, NextResponse } from "next/server";
import camelcaseKeys from "camelcase-keys";
import { generateRandomProxy } from "@/utils";
import { IProxyBaseData, ProxyProtocolType } from "@/types/data";

export async function GET(req: NextRequest) {
  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization"
  }
  try {
    const searchParams = req.nextUrl.searchParams;
    const data: IProxyBaseData[] = [];
    let count = 100;
    const countParam = searchParams.get("count");
    const protocol = searchParams.get("protocol");
    
    if (countParam) {
      count = !Number.isNaN(parseInt(countParam)) ? Math.abs(parseInt(countParam)) : count;
    }

    for (let i = 0; i < count; i++) {
      data.push(protocol ? generateRandomProxy(protocol as ProxyProtocolType) : generateRandomProxy())
    }
    
    return NextResponse.json({ data }, { status: 200, headers });
  } catch (error) {
    console.error("Ошибка при чтении JSON-файла:", error);
    return NextResponse.json({ data: {
        error: true,
        message: "Internal server error"
    } }, { status: 500, headers });
  }
}