/** Legacy PKK deep links are disabled; mirrors backend external_lot_links.pkk_map_url. */
export function pkkMapUrl(cadastralNumber: string | null | undefined): string | null {
  void cadastralNumber;
  return null;
}

export function nspdMapUrl(cadastralNumber: string | null | undefined): string | null {
  return cadastralNumber?.trim() ? "https://nspd.gov.ru/map?thematic=PKK" : null;
}
