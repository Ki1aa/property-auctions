import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TradesPage } from "./TradesPage";

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
  // api.ts always builds absolute URL like http://localhost:8000/...
  return new URL(url);
}

describe("TradesPage", () => {
  beforeEach(() => {
    const calls: FetchCall[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        calls.push({ url });

        const u = parseUrl(url);
        if (u.pathname.endsWith("/api/opendata-notices/facets")) {
          return jsonResponse({ document_type: ["DOC_A"], bidd_type_code: ["BIDD_A"] });
        }
        if (u.pathname.endsWith("/api/opendata-notices")) {
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

    // helper for test access
    (globalThis as unknown as { __fetchCalls: FetchCall[] }).__fetchCalls = calls;
  });

  it("reset sends empty filters and offset=0", async () => {
    render(
      <MemoryRouter>
        <TradesPage />
      </MemoryRouter>,
    );

    // Wait until initial load finished (page subtitle switches from loading)
    await screen.findByText(/Найдено:/);

    fireEvent.change(screen.getByPlaceholderText("Реестровый номер (точное совпадение)"), {
      target: { value: "123" },
    });
    fireEvent.click(screen.getByText("Сбросить"));

    await waitFor(() => {
      const calls = (globalThis as unknown as { __fetchCalls: FetchCall[] }).__fetchCalls;
      expect(calls.length).toBeGreaterThan(0);
      const last = calls[calls.length - 1]!;
      const u = parseUrl(last.url);
      expect(u.pathname.endsWith("/api/opendata-notices")).toBe(true);
      expect(u.searchParams.get("limit")).toBe("50");
      expect(u.searchParams.get("offset")).toBe("0");
      expect(u.searchParams.has("document_type")).toBe(false);
      expect(u.searchParams.has("bidd_type_code")).toBe(false);
      expect(u.searchParams.has("reg_num")).toBe(false);
    });
  });
});

