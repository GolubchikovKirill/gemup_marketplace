import path from "path";
import { promises as fs } from "fs";
import { NextRequest, NextResponse } from "next/server";
import camelcaseKeys from "camelcase-keys";

export async function GET(req: NextRequest) {
  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization"
  }
  try {
    const filePath = path.join(process.cwd(), "public/data/mocks/proxy_products.json");
    const fileContents = await fs.readFile(filePath, "utf8");
    const data = (JSON.parse(fileContents) as Array<any>).map((item) => camelcaseKeys(item));
    
    return NextResponse.json({ data }, { status: 200, headers });
  } catch (error) {
    console.error("Ошибка при чтении JSON-файла:", error);
    return NextResponse.json({ data: {
        error: true,
        message: "Internal server error"
    } }, { status: 500, headers });
  }
}