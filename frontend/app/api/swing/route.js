import { NextResponse } from "next/server";

export async function GET(request) {
  try {
    const incomingUrl = new URL(request.url);
    const lookback = incomingUrl.searchParams.get("lookback");
    const upstreamUrl = new URL("http://127.0.0.1:8000/api/swing");
    if (lookback) {
      upstreamUrl.searchParams.set("lookback", lookback);
    }

    const upstream = await fetch(upstreamUrl.toString(), {
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
