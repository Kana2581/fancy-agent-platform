export type HelpDocumentSummaryOut = {
  id: number;
  slug: string;
  title: string;
  summary: string;
  category?: string | null;
  doc_type: string;
  route?: string | null;
  icon_key?: string | null;
  sort_order: number;
};
