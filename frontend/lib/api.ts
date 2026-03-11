const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type ListingScore = {
  overall_score: number;
  reasoning: string;
  scored_at: string;
} | null;

export type Listing = {
  id: number;
  title: string;
  company: string;
  location: string;
  remote: boolean;
  description: string;
  apply_url: string;
  source: string;
  date_posted: string | null;
  date_fetched: string;
  created_at: string;
  listing_type: string | null;
  score: ListingScore;
};

export type ListingsResponse = {
  total: number;
  items: Listing[];
};

export type GetListingsParams = {
  page?: number;
  limit?: number;
  offset?: number;
  sort?: "date" | "company" | "score";
  min_score?: number;
  max_score?: number;
  remote?: boolean;
  source?: string;
  listing_type?: string;
};

export async function getListings(params: GetListingsParams = {}): Promise<ListingsResponse> {
  const {
    page = 1,
    limit = 25,
    sort = "date",
    min_score,
    max_score,
    remote,
    source,
    listing_type,
  } = params;
  const offset = params.offset ?? (page - 1) * limit;

  const search = new URLSearchParams();
  search.set("limit", String(limit));
  search.set("offset", String(offset));
  search.set("sort", sort);
  if (min_score != null) search.set("min_score", String(min_score));
  if (max_score != null) search.set("max_score", String(max_score));
  if (remote != null) search.set("remote", String(remote));
  if (source != null && source !== "") search.set("source", source);
  if (listing_type != null && listing_type !== "") search.set("listing_type", listing_type);

  const res = await fetch(`${API_URL}/api/listings?${search.toString()}`);
  if (!res.ok) throw new Error(`Listings failed: ${res.status}`);
  return res.json();
}

// ---- Resume ----

export type ResumeData = {
  id: number;
  raw_text: string;
  skills: string[];
  experience: string;
  education: string;
  preferred_roles: string[];
  updated_at: string;
};

export async function getResume(): Promise<{ resume: ResumeData | null }> {
  const res = await fetch(`${API_URL}/api/resume`);
  if (!res.ok) throw new Error(`Resume failed: ${res.status}`);
  return res.json();
}

/** Upload a resume (PDF or DOCX). Parses and stores; replaces previous. */
export async function uploadResume(file: File): Promise<{ ok: boolean; resume?: ResumeData; error?: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_URL}/api/resume/upload`, {
    method: "POST",
    body: form,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) return { ok: false, error: data.error || data.detail || `Upload failed: ${res.status}` };
  if (data.ok === false) return { ok: false, error: data.error || "Upload failed" };
  return { ok: true, resume: data.resume };
}

// ---- Profile (skills, about me — merged with resume for scoring) ----

export type ProfileData = {
  id: number;
  custom_skills: string[];
  about_me: string;
  preferred_roles: string[];
  updated_at: string | null;
};

export async function getProfile(): Promise<{ profile: ProfileData }> {
  const res = await fetch(`${API_URL}/api/profile`);
  if (!res.ok) throw new Error(`Profile failed: ${res.status}`);
  return res.json();
}

export async function updateProfile(profile: {
  custom_skills?: string[];
  about_me?: string;
  preferred_roles?: string[];
}): Promise<{ ok: boolean; profile: ProfileData }> {
  const res = await fetch(`${API_URL}/api/profile`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Profile update failed: ${res.status}`);
  return data;
}

/** Fetch or compute match score for a listing (vs your resume). Requires resume uploaded + GROQ_API_KEY. Use refresh=true to recompute cached score. */
export async function getListingScore(
  listingId: number,
  options?: { refresh?: boolean }
): Promise<{ score: { overall_score: number; reasoning: string; scored_at: string } }> {
  const url = `${API_URL}/api/scores/${listingId}${options?.refresh ? "?refresh=true" : ""}`;
  const res = await fetch(url);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Score failed: ${res.status}`);
  return data;
}

export type CoverLetter = {
  id: number;
  listing_id: number;
  content: string;
  version: number;
  tone: string;
  generated_at: string;
  edited_by_user: boolean;
};

export type ListingDetail = Listing & {
  cover_letters: CoverLetter[];
};

export async function getListingDetail(listingId: number): Promise<ListingDetail> {
  const res = await fetch(`${API_URL}/api/listings/${listingId}`);
  if (!res.ok) throw new Error(`Listing failed: ${res.status}`);
  return res.json();
}

export async function generateCoverLetter(
  listingId: number,
  tone: string = "Professional"
): Promise<{ ok: boolean; cover_letter: CoverLetter }> {
  const res = await fetch(
    `${API_URL}/api/cover-letter/generate?listing_id=${listingId}&tone=${encodeURIComponent(tone)}`,
    { method: "POST" }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Generate failed: ${res.status}`);
  }
  return res.json();
}

export async function updateCoverLetter(
  letterId: number,
  content: string
): Promise<{ ok: boolean; cover_letter: CoverLetter }> {
  const res = await fetch(`${API_URL}/api/cover-letter/${letterId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error(`Update failed: ${res.status}`);
  return res.json();
}

export type ApplyResult = {
  ok: boolean;
  method: string;
  message: string;
  apply_url: string;
  cover_letter_text: string;
};

export async function applyToListing(listingId: number): Promise<ApplyResult> {
  const res = await fetch(`${API_URL}/api/apply/${listingId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm: true }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Apply failed: ${res.status}`);
  return data;
}

// ---- Application Tracker (Phase 6) ----

export type Application = {
  id: number;
  listing_id: number;
  listing_title: string;
  listing_company: string;
  apply_url: string;
  status: string;
  applied_at: string | null;
  apply_method: string;
  notes: string;
  follow_up_date: string | null;
};

export type ApplicationsResponse = {
  items: Application[];
  total: number;
};

export async function getApplications(params: {
  status?: string;
  sort?: "applied_at" | "status" | "company";
} = {}): Promise<ApplicationsResponse> {
  const search = new URLSearchParams();
  if (params.status) search.set("status", params.status);
  if (params.sort) search.set("sort", params.sort);
  const qs = search.toString();
  const res = await fetch(`${API_URL}/api/applications${qs ? `?${qs}` : ""}`);
  if (!res.ok) throw new Error(`Applications failed: ${res.status}`);
  return res.json();
}

export async function updateApplication(
  appId: number,
  body: { status?: string; notes?: string; follow_up_date?: string | null }
): Promise<Application> {
  const res = await fetch(`${API_URL}/api/applications/${appId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Update failed: ${res.status}`);
  return data;
}

export async function saveListingForLater(listingId: number): Promise<Application> {
  const res = await fetch(`${API_URL}/api/applications/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ listing_id: listingId }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Save failed: ${res.status}`);
  return data;
}

export async function exportApplicationsCsv(): Promise<Blob> {
  const res = await fetch(`${API_URL}/api/applications/export?format=csv`);
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  return res.blob();
}
