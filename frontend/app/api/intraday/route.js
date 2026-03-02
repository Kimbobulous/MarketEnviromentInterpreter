import { NextResponse } from "next/server";

export async function GET(request) {
  try {
    const incomingUrl = new URL(request.url);
    const lookback = incomingUrl.searchParams.get("lookback");
    const upstream = new URL("http://127.0.0.1:8000/api/intraday");
    if (lookback) {
      upstream.searchParams.set("lookback", lookback);
    }

    const response = await fetch(upstream.toString(), {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`Backend request failed with status ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      {
        error: error instanceof Error ? error.message : "Proxy request failed",
      },
      { status: 502 }
    );
  }
}
