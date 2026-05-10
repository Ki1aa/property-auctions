import { Link } from "react-router-dom";
import type { Lot } from "../types";

type Props = {
  lot: Lot;
  /** When true, first row is internal SPA card link (for list/table). */
  showInternalCardLink?: boolean;
  /** When true and `app_lot_url` is set, show shareable monitor link (detail page). */
  showAppPublicUrl?: boolean;
};

/**
 * Single-column external links: card, GIS lot, notice, PKK, Domclick (map preferred, else cadastral search).
 */
export function LotExternalLinks({
  lot,
  showInternalCardLink,
  showAppPublicUrl,
}: Props) {
  const pkkUrl = lot.pkk_map_url;
  const nspdExtra =
    lot.nspd_map_url && lot.nspd_map_url !== pkkUrl ? lot.nspd_map_url : null;
  const domclickHref = lot.domclick_map_url ?? lot.domclick_search_url_cadastral ?? null;
  const domclickTitle = lot.domclick_map_url
    ? "Домклик: объявления на карте вокруг координат участка (НСПД или извещение)"
    : "Домклик: текстовый поиск по кадастровому номеру (координат для карты нет)";

  return (
    <div className="lot-external-links">
      {showAppPublicUrl && lot.app_lot_url ? (
        <a className="lot-external-links__item" href={lot.app_lot_url} target="_blank" rel="noreferrer">
          Карточка в мониторе
        </a>
      ) : null}
      {showInternalCardLink ? (
        <Link to={`/lots/${lot.id}`} className="lot-external-links__item">
          Карточка
        </Link>
      ) : null}
      {lot.torgi_url ? (
        <a className="lot-external-links__item" href={lot.torgi_url} target="_blank" rel="noreferrer">
          Лот
        </a>
      ) : null}
      {lot.torgi_notice_url ? (
        <a className="lot-external-links__item" href={lot.torgi_notice_url} target="_blank" rel="noreferrer">
          Извещение
        </a>
      ) : null}
      {pkkUrl ? (
        <a
          className="lot-external-links__item"
          href={pkkUrl}
          target="_blank"
          rel="noreferrer"
          title="Публичная кадастровая карта (НСПД): участок на карте при наличии координат или поиск по кадастру"
        >
          ПКК
        </a>
      ) : null}
      {nspdExtra ? (
        <a
          className="lot-external-links__item"
          href={nspdExtra}
          target="_blank"
          rel="noreferrer"
          title="Карта НСПД с обогащением (центроид / карточка)"
        >
          НСПД (карточка)
        </a>
      ) : null}
      {domclickHref ? (
        <a
          className="lot-external-links__item"
          href={domclickHref}
          target="_blank"
          rel="noreferrer"
          title={domclickTitle}
        >
          Домклик
        </a>
      ) : null}
    </div>
  );
}
