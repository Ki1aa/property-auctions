export type Notice = {
  id: number;
  reg_num: string;
  document_type: string | null;
  publish_date: string | null;
  bidd_type_code: string | null;
  href: string;
};

export type NoticeListPage = {
  items: Notice[];
  total: number;
  limit: number;
  offset: number;
};

export type LotsSort =
  | "updated_at_desc"
  | "price_per_sotka_asc"
  | "price_per_sotka_desc"
  | "discount_to_baseline_desc";

export type Lot = {
  id: number;
  source_id: string;
  title: string;
  status: string | null;
  region: string | null;
  category: string | null;
  start_price: number | null;
  current_price: number | null;
  start_date: string | null;
  end_date: string | null;
  cadastral_number: string | null;
  area_sqm: number | null;
  is_izhs_candidate: boolean;
  /** Rub per sotka (100 m²) from notice; not market valuation. */
  start_price_per_sotka: number | null;
  /** Rub per m² from notice. */
  start_price_per_sqm: number | null;
  /** Internal auction baseline, not external market valuation. */
  baseline_price_per_sotka: number | null;
  /** Positive means the lot is cheaper than the internal baseline. */
  discount_to_baseline: number | null;
  valuation_confidence: "low" | "medium" | "high" | string | null;
  valuation_baseline_scope: string | null;
  valuation_baseline_sample_size: number | null;
  valuation_reason: string | null;
};

export type LotListPage = {
  items: Lot[];
  total: number;
  limit: number;
  offset: number;
};

export type LotDetail = Lot & {
  latitude: number | null;
  longitude: number | null;
  source_url: string | null;
  organizer_name: string | null;
  organizer_inn: string | null;
  land_category: string | null;
  permitted_use: string | null;
  address: string | null;
  notice_detail_url: string | null;
  opendata_notice_id: number | null;
  notice_payload: Record<string, unknown> | null;
};

export type MapPoint = {
  lot_id: number;
  title: string;
  status: string | null;
  latitude: number;
  longitude: number;
};

export type IngestRun = {
  id: number;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  fetched_count: number;
  upserted_count: number;
  changed_count: number;
  processed_files: number;
  failed_files: number;
  last_error_source_url: string | null;
  error_kind: string | null;
  error_message: string | null;
};

export type LotFacets = {
  category: string[];
  status: string[];
  region: string[];
};

export type OpenDataNoticeFacets = {
  bidd_type_code: string[];
  document_type: string[];
};
