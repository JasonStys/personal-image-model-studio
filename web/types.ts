/** Small browser contracts for bounded workspace metadata. */
// Index: declarations Item@L3, Job@L11, Workspace@L19; variables none. Purposes/parameters: docs/code-map.json.
export interface Item {
  id: string;
  name: string;
  kind?: string;
  details?: Record<string, unknown>;
  counts?: { total: number; flagged: number };
  request?: { prompt?: { description?: string } } | null;
}
export interface Job {
  id: string;
  kind: string;
  status: string;
  progress: Record<string, number>;
  error?: string;
  result?: unknown;
}
export interface Workspace {
  model: Item[];
  dataset: Item[];
  image: Item[];
  job: Job[];
}
