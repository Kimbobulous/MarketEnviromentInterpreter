import { NextResponse } from "next/server";

export async function GET() {
  try {
    const upstream = await fetch("http://127.0.0.1:8000/api/swing", {
      cache: "no-store",
    });

    const body = await upstream.text();
    return new NextResponse(body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") || "application/json",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Upstream backend unavailable" },
      { status: 502 }
    );
  }
}
