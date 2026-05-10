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

export type NoticeSort =
  | "publish_date_desc"
  | "publish_date_asc"
  | "reg_num_asc"
  | "reg_num_desc"
  | "document_type_asc"
  | "document_type_desc"
  | "bidd_type_code_asc"
  | "bidd_type_code_desc";

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
  created_at: string | null;
  updated_at: string | null;
  /** Notice or dataset URL on torgi.gov.ru when known. */
  source_url: string | null;
  cadastral_number: string | null;
  area_sqm: number | null;
  municipality: string | null;
  settlement: string | null;
  is_izhs_candidate: boolean;
  notice_reg_num: string | null;
  notice_lot_number: string | null;
  notice_lot_count: number | null;
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
  /** NSPD: none | enriched | no_data */
  nspd_data_status: string | null;
  map_centroid_available: boolean;
  /** Median from imported comparables; optional. */
  market_baseline_price_per_sotka: number | null;
  discount_to_market: number | null;
  market_valuation_reason: string | null;
  investment_score: number | null;
  app_lot_url: string | null;
  /** Concrete GIS Torgi lot page. */
  torgi_url: string | null;
  /** GIS Torgi notice page. */
  torgi_notice_url: string | null;
  /** Raw notice JSON href when it differs from the HTML notice page. */
  torgi_json_url: string | null;
  /** NSPD public map entry point; cadastral number is shown separately for search. */
  nspd_map_url: string | null;
  /** Публичная кадастровая карта (ПКК) на nspd.gov.ru — поиск по кадастровому номеру. */
  pkk_map_url: string | null;
  /** Домклик: карта объявлений о продаже участков в округе (оценка рынка вручную). */
  domclick_map_url: string | null;
  domclick_search_url: string | null;
  domclick_search_url_cadastral: string | null;
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
  organizer_name: string | null;
  organizer_inn: string | null;
  land_category: string | null;
  permitted_use: string | null;
  permitted_use_codes: string | null;
  address: string | null;
  notice_detail_url: string | null;
  opendata_notice_id: number | null;
  notice_payload: Record<string, unknown> | null;
  nspd_specified_area_sqm: number | null;
  nspd_readable_address: string | null;
  nspd_cost_value: number | null;
  nspd_centroid_latitude: number | null;
  nspd_centroid_longitude: number | null;
  nspd_card_id: string | null;
  nspd_card_type: string | null;
  nspd_enriched_at: string | null;
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

export type IngestStatus = {
  is_running: boolean;
  scheduler_running: boolean;
  next_run_at: string | null;
  ingest_mode: string;
  interval_minutes: number;
  run_on_startup: boolean;
  fetch_notice_details: boolean;
  detail_max_per_run: number;
  target_region_codes: string;
  telegram_digest_enabled: boolean;
  telegram_digest_interval_minutes: number;
  telegram_digest_next_at: string | null;
};

export type ManualIngestStartResponse = {
  started: boolean;
  message: string;
};

export type LotFacets = {
  category: string[];
  status: string[];
  region: string[];
  municipality: string[];
};

export type OpenDataNoticeFacets = {
  bidd_type_code: string[];
  document_type: string[];
};

export type LotQualityMetrics = {
  region: string | null;
  total: number;
  izhs_candidates: number;
  with_municipality: number;
  with_cadastral: number;
  with_area: number;
  with_start_price: number;
  with_price_per_sotka: number;
  with_baseline: number;
  with_positive_discount: number;
  with_nspd_enriched: number;
  with_map_centroid: number;
};
