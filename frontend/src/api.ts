import { IngestRun, Lot, LotDetail, MapPoint, Notice } from "./types";

const baseUrl = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000") as string;

async function request<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const query = new URLSearchParams();
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") {
        query.set(key, String(value));
      }
    }
  }
  const qs = query.toString();
  const url = `${baseUrl}${path}${qs ? `?${qs}` : ""}`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Запрос ${path} не удался: HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchNotices(params: {
  documentType?: string;
  biddTypeCode?: string;
  regNum?: string;
  limit?: number;
}): Promise<Notice[]> {
  return request<Notice[]>("/api/opendata-notices", {
    document_type: params.documentType,
    bidd_type_code: params.biddTypeCode,
    reg_num: params.regNum,
    limit: params.limit,
  });
}

export function fetchLots(params: {
  region?: string;
  status?: string;
  category?: string;
  isIzhs?: boolean;
  minArea?: number;
  maxArea?: number;
  maxStartPrice?: number;
  cadastralNumber?: string;
  limit?: number;
}): Promise<Lot[]> {
  return request<Lot[]>("/api/lots", {
    region: params.region,
    status: params.status,
    category: params.category,
    is_izhs: params.isIzhs === undefined ? undefined : params.isIzhs ? "true" : "false",
    min_area: params.minArea,
    max_area: params.maxArea,
    max_start_price: params.maxStartPrice,
    cadastral_number: params.cadastralNumber,
    limit: params.limit,
  });
}

export function fetchLot(id: number | string): Promise<LotDetail> {
  return request<LotDetail>(`/api/lots/${id}`);
}

export function fetchMapPoints(): Promise<MapPoint[]> {
  return request<MapPoint[]>("/api/lots-map");
}

export function fetchIngestRuns(limit = 50): Promise<IngestRun[]> {
  return request<IngestRun[]>("/api/ingest-runs", { limit });
}
