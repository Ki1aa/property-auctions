import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  try {
    return new URL(url);
  } catch {
    return new URL(url, "http://localhost/");
  }
}

function noticeCalls(): FetchCall[] {
  const calls = (globalThis as unknown as { __fetchCalls: FetchCall[] }).__fetchCalls;
  return calls.filter((c) => parseUrl(c.url).pathname.endsWith("/api/opendata-notices"));
}

describe("TradesPage", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

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
            items: [
              {
                id: 1,
                reg_num: "23000012770000000082",
                document_type: "notice",
                publish_date: "2026-05-07T23:50:49",
                bidd_type_code: "ZK",
                href: "https://example.com/notice.json",
              },
            ],
            total: 1,
            limit: Number(u.searchParams.get("limit") ?? 0),
            offset: Number(u.searchParams.get("offset") ?? 0),
          });
        }
        return new Response("Not found", { status: 404 });
      }) as unknown as typeof fetch,
    );

    (globalThis as unknown as { __fetchCalls: FetchCall[] }).__fetchCalls = calls;
  });

  it("reset sends empty filters, default sort and offset=0", async () => {
    render(
      <MemoryRouter>
        <TradesPage />
      </MemoryRouter>,
    );

    await screen.findByText(/Найдено:/);

    fireEvent.change(screen.getByPlaceholderText("Точное совпадение"), {
      target: { value: "123" },
    });
    fireEvent.click(screen.getByText("Сбросить"));

    await waitFor(() => {
      const calls = noticeCalls();
      const last = calls[calls.length - 1]!;
      const u = parseUrl(last.url);
      expect(u.searchParams.get("limit")).toBe("50");
      expect(u.searchParams.get("offset")).toBe("0");
      expect(u.searchParams.get("sort")).toBe("publish_date_desc");
      expect(u.searchParams.has("document_type")).toBe(false);
      expect(u.searchParams.has("bidd_type_code")).toBe(false);
      expect(u.searchParams.has("reg_num")).toBe(false);
    });
  });

  it("sorts by clicked column on the server and resets to first page", async () => {
    render(
      <MemoryRouter>
        <TradesPage />
      </MemoryRouter>,
    );

    await screen.findByText(/Найдено:/);
    fireEvent.click(screen.getByRole("button", { name: /Реестровый номер/ }));

    await waitFor(() => {
      const calls = noticeCalls();
      const last = calls[calls.length - 1]!;
      const u = parseUrl(last.url);
      expect(u.searchParams.get("sort")).toBe("reg_num_asc");
      expect(u.searchParams.get("offset")).toBe("0");
    });

    fireEvent.click(screen.getByRole("button", { name: /Реестровый номер/ }));

    await waitFor(() => {
      const calls = noticeCalls();
      const last = calls[calls.length - 1]!;
      const u = parseUrl(last.url);
      expect(u.searchParams.get("sort")).toBe("reg_num_desc");
      expect(u.searchParams.get("offset")).toBe("0");
    });
  });
});
