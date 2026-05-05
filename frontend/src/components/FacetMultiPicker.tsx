import { useEffect, useMemo, useRef, useState } from "react";

export type FacetMultiPickerProps = {
  label: string;
  options: string[];
  value: string[];
  onChange: (next: string[]) => void;
};

function sortedCopy(values: string[]): string[] {
  return [...values].sort();
}

function summaryText(value: string[]): string {
  if (value.length === 0) return "Все";
  const s = sortedCopy(value);
  if (s.length === 1) return s[0]!;
  if (s.length <= 3) return s.join(", ");
  return `${s.length} выбрано`;
}

export function FacetMultiPicker({ label, options, value, onChange }: FacetMultiPickerProps) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<string[]>(() => sortedCopy(value));
  const rootRef = useRef<HTMLDivElement>(null);

  const summary = useMemo(() => summaryText(value), [value]);

  useEffect(() => {
    if (!open) return;
    function onDocMouseDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocMouseDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onDocMouseDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  function handleTriggerClick() {
    if (open) {
      setOpen(false);
      return;
    }
    setDraft(sortedCopy(value));
    setOpen(true);
  }

  function toggleOption(code: string) {
    setDraft((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  }

  function apply() {
    onChange(sortedCopy(draft));
    setOpen(false);
  }

  function clearDraft() {
    setDraft([]);
  }

  return (
    <div className="filters__field facet-picker" ref={rootRef}>
      <span className="filters__facet-label">{label}</span>
      <button
        type="button"
        className="facet-picker__trigger"
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={handleTriggerClick}
      >
        <span className="facet-picker__trigger-text">{summary}</span>
        <span className="facet-picker__trigger-chevron" aria-hidden>
          {open ? "\u25B2" : "\u25BC"}
        </span>
      </button>
      {open && (
        <div className="facet-picker__panel" role="dialog" aria-label={label}>
          <div className="facet-picker__scroll">
            {options.map((code) => (
              <label key={code} className="checkbox facet-picker__row">
                <input
                  type="checkbox"
                  checked={draft.includes(code)}
                  onChange={() => toggleOption(code)}
                />
                <span>{code}</span>
              </label>
            ))}
          </div>
          <div className="facet-picker__toolbar">
            <button type="button" className="button button--ghost button--compact" onClick={clearDraft}>
              Очистить
            </button>
            <div className="facet-picker__toolbar-spacer" />
            <button type="button" className="button button--ghost button--compact" onClick={() => setOpen(false)}>
              Отмена
            </button>
            <button type="button" className="button button--compact" onClick={apply}>
              Применить
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
