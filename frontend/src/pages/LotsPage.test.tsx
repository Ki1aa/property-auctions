import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { LotsPage } from "./LotsPage";

type FetchCall = {
  url: string;
};

function jsonResponse(data: unknown): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function parseUrl(url: string): URL {
  try {
    return new URL(url);
  } catch {
    return new URL(url, "http://localhost/");
  }
}

function LocationProbe() {
  const loc = useLocation();
  return <div data-testid="location">{`${loc.pathname}${loc.search}`}</div>;
}

describe("LotsPage", () => {
  beforeEach(() => {
    const calls: FetchCall[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        calls.push({ url });
        const u = parseUrl(url);

        if (u.pathname.endsWith("/api/lots/facets")) {
          return jsonResponse({ region: ["72"], status: ["A"], category: ["A", "B"] });
        }
        if (u.pathname.endsWith("/api/lots")) {
          return jsonResponse({
            items: [],
            total: 0,
            limit: Number(u.searchParams.get("limit") ?? 0),
            offset: Number(u.searchParams.get("offset") ?? 0),
          });
        }
        return new Response("Not found", { status: 404 });
      }) as unknown as typeof fetch,
    );

    (globalThis as unknown as { __fetchCalls: FetchCall[] }).__fetchCalls = calls;
  });

  it("reads initial state from URL and reset clears query params", async () => {
    render(
      <MemoryRouter initialEntries={["/lots?region=72&sort=price_per_sotka_asc&offset=50&category=A&category=B"]}>
        <Routes>
          <Route path="/lots" element={<><LocationProbe /><LotsPage /></>} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      const calls = (globalThis as unknown as { __fetchCalls: FetchCall[] }).__fetchCalls;
      const firstLotsCall = calls.find((c) => parseUrl(c.url).pathname.endsWith("/api/lots"));
      expect(firstLotsCall).toBeTruthy();
      const u = parseUrl(firstLotsCall!.url);
      expect(u.searchParams.get("region")).toBe("72");
      expect(u.searchParams.get("sort")).toBe("price_per_sotka_asc");
      expect(u.searchParams.get("offset")).toBe("50");
      expect(u.searchParams.getAll("category").sort()).toEqual(["A", "B"]);
    });

    fireEvent.click(screen.getByText("Сбросить"));

    await waitFor(() => {
      expect(screen.getByTestId("location").textContent).toBe("/lots");
    });

    await waitFor(() => {
      const calls = (globalThis as unknown as { __fetchCalls: FetchCall[] }).__fetchCalls;
      const lotsCalls = calls.filter((c) => parseUrl(c.url).pathname.endsWith("/api/lots"));
      expect(lotsCalls.length).toBeGreaterThanOrEqual(2);
      const last = lotsCalls[lotsCalls.length - 1]!;
      const u = parseUrl(last.url);
      expect(u.searchParams.get("limit")).toBe("50");
      expect(u.searchParams.get("offset")).toBe("0");
      // reset clears applied params
      expect(u.searchParams.has("region")).toBe(false);
      expect(u.searchParams.has("category")).toBe(false);
      // default sort is still sent to API after reset
      expect(u.searchParams.get("sort")).toBe("updated_at_desc");
    });
  });
});

