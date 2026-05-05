type Props = {
  status: string | null | undefined;
  variant?: "ingest" | "lot" | "auto";
};

const ingestVariantMap: Record<string, "success" | "warn" | "error"> = {
  success: "success",
  noop: "warn",
  partial_failed: "warn",
  running: "warn",
  failed: "error",
};

function pickClass(status: string, variant: Props["variant"]): string {
  if (variant === "ingest") {
    return ingestVariantMap[status] ? `badge badge--${ingestVariantMap[status]}` : "badge";
  }
  const lowered = status.toLowerCase();
  if (lowered.includes("active") || lowered.includes("publish") || lowered.includes("notice")) {
    return "badge badge--success";
  }
  if (lowered.includes("cancel") || lowered.includes("fail") || lowered.includes("annul")) {
    return "badge badge--error";
  }
  if (lowered.includes("draft") || lowered.includes("pending") || lowered.includes("partial")) {
    return "badge badge--warn";
  }
  return "badge";
}

export function StatusBadge({ status, variant = "auto" }: Props) {
  if (!status) {
    return <span className="badge">—</span>;
  }
  return <span className={pickClass(status, variant)}>{status}</span>;
}
