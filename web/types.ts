/** Small browser contracts for bounded workspace metadata. */
// Index: declarations Item@L3, Job@L11, Workspace@L19, DatasetReview@L27; variables none. Purposes/parameters: docs/code-map.json.
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

/** Read-only local dataset evidence; sample limits and uncertainty are part of the displayed contract. */
export interface DatasetReview {
  schema: number;
  dataset_fingerprint: string;
  report_sha256: string;
  counts: Record<string, number>;
  origins: Record<string, number>;
  minimum_training_counts_met: boolean;
  inspection: {
    maximum_images: number;
    maximum_file_bytes: number;
    maximum_pixels: number;
    verified_images: number;
    remaining_eligible_not_verified: number;
    cross_split_comparisons: number;
    budget_stopped: boolean;
    integrity_errors: { hash: string; name: string; reason: string }[];
  };
  near_duplicate_candidates: {
    left: { hash: string; name: string; split: string };
    right: { hash: string; name: string; split: string };
    difference_bits: number;
  }[];
  candidate_pairs_total: number;
  candidate_pairs_not_shown: number;
  method: string;
  limitations: string[];
}
