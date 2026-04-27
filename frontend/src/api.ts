import { Notice } from "./types";

const baseUrl = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000") as string;

export async function fetchNotices(params: {
  documentType?: string;
  biddTypeCode?: string;
  regNum?: string;
}): Promise<Notice[]> {
  const query = new URLSearchParams();
  if (params.documentType) query.set("document_type", params.documentType);
  if (params.biddTypeCode) query.set("bidd_type_code", params.biddTypeCode);
  if (params.regNum) query.set("reg_num", params.regNum);
  const response = await fetch(`${baseUrl}/api/opendata-notices?${query.toString()}`);
  if (!response.ok) throw new Error("Не удалось загрузить список извещений");
  return response.json();
}
