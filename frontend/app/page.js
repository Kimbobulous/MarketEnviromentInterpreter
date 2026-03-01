"use client";

import { useEffect, useState } from "react";

export default function HomePage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchIntraday() {
      try {
        setLoading(true);
        setError("");

        const response = await fetch("/api/intraday");
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }

        const json = await response.json();
        setData(json);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    fetchIntraday();
  }, []);

  return (
    <main style={{ fontFamily: "sans-serif", padding: "1rem" }}>
      <h1>Market Environment Interpreter</h1>
      <p>Fetching: /api/intraday</p>
      <p>Proxy target: http://127.0.0.1:8000/api/intraday</p>
      {loading && <p>Loading...</p>}
      {error && <p>Error: {error}</p>}
      <pre style={{ whiteSpace: "pre-wrap" }}>
        {data ? JSON.stringify(data, null, 2) : "{}"}
      </pre>
    </main>
  );
}
