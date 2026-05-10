import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { buildLotsExportUrl, fetchLotFacets, fetchLots } from "../api";
import { FacetMultiPicker } from "../components/FacetMultiPicker";
import { LotsTable } from "../components/LotsTable";
import { FACET_SINGLE_SELECT_MAX } from "../facetFilterUi";
import { Lot, LotFacets, LotsSort } from "../types";

const PAGE_SIZE = 50;
const DEFAULT_SORT: LotsSort = "updated_at_desc";

type LotsQueryState = {
  region: string;
  status: string;
  municipality: string;
  categories: string[];
  isIzhs: boolean;
  hasCadastral: boolean;
  minArea: string;
  maxArea: string;
  maxStartPrice: string;
  cadastral: string;
  sort: LotsSort;
  offset: number;
};

function parseLotsSort(value: string | null): LotsSort {
  if (
    value === "price_per_sotka_asc" ||
    value === "price_per_sotka_desc" ||
    value === "discount_to_baseline_desc" ||
    value === "updated_at_desc"
  ) {
    return value;
  }
  return DEFAULT_SORT;
}

function parseOffset(value: string | null): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : 0;
}

function normalizeRegionInput(value: string): string {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .join(",");
}

function queryStateFromSearchParams(params: URLSearchParams): LotsQueryState {
  return {
    region: params.get("region") ?? "",
    status: params.get("status") ?? "",
    municipality: params.get("municipality") ?? "",
    categories: params.getAll("category"),
    isIzhs: params.get("is_izhs") === "true",
    hasCadastral: params.get("has_cadastral") === "true",
    minArea: params.get("min_area") ?? "",
    maxArea: params.get("max_area") ?? "",
    maxStartPrice: params.get("max_start_price") ?? "",
    cadastral: params.get("cadastral_number") ?? "",
    sort: parseLotsSort(params.get("sort")),
    offset: parseOffset(params.get("offset")),
  };
}

function optionalNumber(value: string): number | undefined {
  return value ? Number(value) : undefined;
}

export function LotsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = queryStateFromSearchParams(searchParams);
  const [lots, setLots] = useState<Lot[]>([]);
  const [total, setTotal] = useState(0);
  const [sort, setSort] = useState<LotsSort>(initialQuery.sort);
  const [offset, setOffset] = useState(initialQuery.offset);
  const [region, setRegion] = useState(initialQuery.region);
  const [status, setStatus] = useState(initialQuery.status);
  const [municipality, setMunicipality] = useState(initialQuery.municipality);
  const [categories, setCategories] = useState<string[]>(initialQuery.categories);
  const [isIzhs, setIsIzhs] = useState(initialQuery.isIzhs);
  const [hasCadastral, setHasCadastral] = useState(initialQuery.hasCadastral);
  const [minArea, setMinArea] = useState(initialQuery.minArea);
  const [maxArea, setMaxArea] = useState(initialQuery.maxArea);
  const [maxStartPrice, setMaxStartPrice] = useState(initialQuery.maxStartPrice);
  const [cadastral, setCadastral] = useState(initialQuery.cadastral);
  const [facets, setFacets] = useState<LotFacets | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const statusOptions = useMemo(() => {
    const s = new Set([...(facets?.status ?? []), ...(status ? [status] : [])]);
    return Array.from(s).sort();
  }, [facets, status]);

  const categoryOptions = useMemo(() => {
    const s = new Set([...(facets?.category ?? []), ...categories]);
    return Array.from(s).sort();
  }, [facets, categories]);

  const municipalityOptions = useMemo(() => {
    const s = new Set([...(facets?.municipality ?? []), ...(municipality ? [municipality] : [])]);
    return Array.from(s).sort();
  }, [facets, municipality]);

  const exportUrl = useMemo(() => {
    const applied = queryStateFromSearchParams(searchParams);
    return buildLotsExportUrl({
      region: applied.region || undefined,
      status: applied.status || undefined,
      municipality: applied.municipality || undefined,
      category: applied.categories.length ? applied.categories : undefined,
      isIzhs: applied.isIzhs ? true : undefined,
      hasCadastral: applied.hasCadastral ? true : undefined,
      minArea: optionalNumber(applied.minArea),
      maxArea: optionalNumber(applied.maxArea),
      maxStartPrice: optionalNumber(applied.maxStartPrice),
      cadastralNumber: applied.cadastral || undefined,
      sort: applied.sort,
      maxRows: 50_000,
    });
  }, [searchParams]);

  const statusAsSelect =
    Boolean(facets) && statusOptions.length > 0 && statusOptions.length <= FACET_SINGLE_SELECT_MAX;
  const municipalityAsSelect =
    Boolean(facets) && municipalityOptions.length > 0 && municipalityOptions.length <= FACET_SINGLE_SELECT_MAX;

  async function load(query: LotsQueryState) {
    try {
      setError("");
      setIsLoading(true);
      const page = await fetchLots({
        region: query.region || undefined,
        status: query.status || undefined,
        municipality: query.municipality || undefined,
        category: query.categories.length ? query.categories : undefined,
        isIzhs: query.isIzhs ? true : undefined,
        hasCadastral: query.hasCadastral ? true : undefined,
        minArea: optionalNumber(query.minArea),
        maxArea: optionalNumber(query.maxArea),
        maxStartPrice: optionalNumber(query.maxStartPrice),
        cadastralNumber: query.cadastral || undefined,
        limit: PAGE_SIZE,
        offset: query.offset,
        sort: query.sort,
      });
      setLots(page.items);
      setTotal(page.total);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }

  function syncFormState(query: LotsQueryState) {
    setRegion(query.region);
    setStatus(query.status);
    setMunicipality(query.municipality);
    setCategories(query.categories);
    setIsIzhs(query.isIzhs);
    setHasCadastral(query.hasCadastral);
    setMinArea(query.minArea);
    setMaxArea(query.maxArea);
    setMaxStartPrice(query.maxStartPrice);
    setCadastral(query.cadastral);
    setSort(query.sort);
    setOffset(query.offset);
  }

  function draftToSearchParams(nextOffset: number, nextSort: LotsSort): URLSearchParams {
    const next = new URLSearchParams();
    const normalizedRegion = normalizeRegionInput(region);
    if (normalizedRegion) next.set("region", normalizedRegion);
    if (status) next.set("status", status);
    if (municipality) next.set("municipality", municipality);
    for (const c of categories) {
      next.append("category", c);
    }
    if (isIzhs) next.set("is_izhs", "true");
    if (hasCadastral) next.set("has_cadastral", "true");
    if (minArea) next.set("min_area", minArea);
    if (maxArea) next.set("max_area", maxArea);
    if (maxStartPrice) next.set("max_start_price", maxStartPrice);
    if (cadastral) next.set("cadastral_number", cadastral);
    if (nextSort !== DEFAULT_SORT) next.set("sort", nextSort);
    if (nextOffset > 0) next.set("offset", String(nextOffset));
    return next;
  }

  function updateAppliedSearchParams(nextOffset: number, nextSort = sort) {
    const next = new URLSearchParams(searchParams);
    if (nextSort === DEFAULT_SORT) {
      next.delete("sort");
    } else {
      next.set("sort", nextSort);
    }
    if (nextOffset > 0) {
      next.set("offset", String(nextOffset));
    } else {
      next.delete("offset");
    }
    setSearchParams(next, { replace: true });
  }

  useEffect(() => {
    void fetchLotFacets()
      .then(setFacets)
      .catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    const query = queryStateFromSearchParams(searchParams);
    syncFormState(query);
    void load(query);
  }, [searchParams]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSearchParams(draftToSearchParams(0, sort), { replace: true });
  }

  function handleReset() {
    const next = new URLSearchParams();
    const emptyQuery = queryStateFromSearchParams(next);
    syncFormState(emptyQuery);
    if (searchParams.toString() === next.toString()) {
      void load(emptyQuery);
      return;
    }
    setSearchParams(next, { replace: true });
  }

  const pageFrom = total === 0 ? 0 : offset + 1;
  const pageTo = offset + lots.length;

  return (
    <div className="page">
      <h1>Лоты</h1>
      <p className="page__subtitle">
        Найдено: {isLoading ? "…" : total}
        {!isLoading && total > 0 ? ` · записи ${pageFrom}—${pageTo}` : ""}
      </p>

      <form className="filters lots-filters" onSubmit={handleSubmit}>
        <label className="filters__field lots-filters__field--region">
          <span className="filters__facet-label">Регион</span>
          <input
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            placeholder="Коды через запятую: 72, 86"
          />
        </label>

        {municipalityAsSelect ? (
          <label className="filters__field lots-filters__field--municipality">
            <span className="filters__facet-label">Муниципалитет</span>
            <select className="filters__select" value={municipality} onChange={(e) => setMunicipality(e.target.value)}>
              <option value="">Все</option>
              {municipalityOptions.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <label className="filters__field lots-filters__field--municipality">
            <span className="filters__facet-label">Муниципалитет</span>
            <input
              value={municipality}
              onChange={(e) => setMunicipality(e.target.value)}
              placeholder="Название муниципалитета"
            />
          </label>
        )}

        {statusAsSelect ? (
          <label className="filters__field lots-filters__field--status">
            <span className="filters__facet-label">Тип документа</span>
            <select className="filters__select" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">Все</option>
              {statusOptions.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <label className="filters__field lots-filters__field--status">
            <span className="filters__facet-label">Тип документа</span>
            <input value={status} onChange={(e) => setStatus(e.target.value)} placeholder="Код documentType" />
          </label>
        )}

        {categoryOptions.length > 0 && (
          <div className="lots-filters__field--category">
            <FacetMultiPicker
              label="Вид торгов"
              options={categoryOptions}
              value={categories}
              onChange={setCategories}
            />
          </div>
        )}

        <label className="filters__field lots-filters__field--cadastral">
          <span className="filters__facet-label">Кадастр</span>
          <input value={cadastral} onChange={(e) => setCadastral(e.target.value)} placeholder="Номер или часть номера" />
        </label>

        <label className="filters__field lots-filters__field--area">
          <span className="filters__facet-label">Площадь от, м²</span>
          <input value={minArea} onChange={(e) => setMinArea(e.target.value)} placeholder="От" type="number" min={0} />
        </label>

        <label className="filters__field lots-filters__field--area">
          <span className="filters__facet-label">Площадь до, м²</span>
          <input value={maxArea} onChange={(e) => setMaxArea(e.target.value)} placeholder="До" type="number" min={0} />
        </label>

        <label className="filters__field lots-filters__field--price">
          <span className="filters__facet-label">Макс. цена</span>
          <input
            value={maxStartPrice}
            onChange={(e) => setMaxStartPrice(e.target.value)}
            placeholder="Стартовая цена, ₽"
            type="number"
            min={0}
          />
        </label>

        <div className="quick-filters lots-filters__quick">
          <label className="checkbox">
            <input type="checkbox" checked={isIzhs} onChange={(e) => setIsIzhs(e.target.checked)} />
            <span>Только ИЖС</span>
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={hasCadastral} onChange={(e) => setHasCadastral(e.target.checked)} />
            <span>С кадастром</span>
          </label>
        </div>

        <label className="filters__field lots-filters__field--sort">
          <span className="filters__facet-label">Сортировка</span>
          <select
            className="filters__select"
            value={sort}
            onChange={(e) => {
              const nextSort = e.target.value as LotsSort;
              setSort(nextSort);
              updateAppliedSearchParams(0, nextSort);
            }}
          >
            <option value="updated_at_desc">По дате обновления</option>
            <option value="discount_to_baseline_desc">По дисконту к baseline</option>
            <option value="price_per_sotka_asc">Старт. цена за сотку: дешевле первые</option>
            <option value="price_per_sotka_desc">Старт. цена за сотку: дороже первые</option>
          </select>
        </label>

        <div className="filters__actions lots-filters__actions">
          <button type="submit">Применить</button>
          <button type="button" className="button button--ghost" onClick={handleReset}>
            Сбросить
          </button>
          <a className="button button--ghost" href={exportUrl} download="lots_export.csv">
            Скачать CSV
          </a>
        </div>
      </form>

      {error && <p className="error">{error}</p>}
      {!isLoading && total > PAGE_SIZE ? (
        <div className="pagination">
          <button
            type="button"
            className="button button--ghost"
            disabled={offset === 0}
            onClick={() => updateAppliedSearchParams(Math.max(0, offset - PAGE_SIZE))}
          >
            Назад
          </button>
          <button
            type="button"
            className="button button--ghost"
            disabled={offset + PAGE_SIZE >= total}
            onClick={() => updateAppliedSearchParams(offset + PAGE_SIZE)}
          >
            Вперёд
          </button>
        </div>
      ) : null}
      {isLoading ? <p className="loading">Загрузка…</p> : <LotsTable lots={lots} />}
    </div>
  );
}
