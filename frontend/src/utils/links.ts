/** PKK deep link; mirrors backend external_lot_links.pkk_map_url. */
export function pkkMapUrl(cadastralNumber: string | null | undefined): string | null {
  if (!cadastralNumber?.trim()) return null;
  const c = cadastralNumber.trim();
  const enc = encodeURIComponent(c);
  return `https://pkk.rosreestr.ru/#/search/${enc}/?text=${enc}`;
}
