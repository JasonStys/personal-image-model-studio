/** Private same-origin transport. Session tokens never accompany third-party requests. */
// Index: declarations privateMode@L7, legacySession@L13, account@L25, transport@L47, connect@L64, api@L72, download@L88, imageUrl@L100, upload@L107; variables token@L3, privateAccounts@L4, path@L26, method@L27, body@L28, response@L30, result@L38, path@L47, method@L47, body@L47, value@L64, path@L73, method@L74, body@L75, response@L77, error@L79, path@L88, name@L88, response@L89, url@L91, link@L92, identity@L100, response@L101, file@L107, data@L110, resolve@L110, reject@L110, reader@L111. Purposes/parameters: docs/code-map.json.
let token = "";
let privateAccounts = false;

/** Sticky account transport: no token storage or fallback to the old plaintext workspace. */
export function privateMode() {
  privateAccounts = true;
  token = "";
}

/** Explicit developer-only session-link compatibility; never invoked by account mode. */
export function legacySession() {
  if (privateAccounts)
    throw new Error("Developer sessions are disabled in account mode.");
  token =
    new URLSearchParams(location.hash.slice(1)).get("token") ||
    sessionStorage.getItem("image-studio-token") ||
    "";
  if (token) sessionStorage.setItem("image-studio-token", token);
  history.replaceState(null, "", location.pathname);
}

/** Cookie-based same-origin account requests; keep credentials out of URLs and JS storage. */
export async function account<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch("/private/" + path, {
    method,
    credentials: "same-origin",
    cache: "no-store",
    redirect: "error",
    headers: { "Content-Type": "application/json", "X-PIMS-Request": "v1" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok)
    throw Object.assign(new Error(result.detail || "Account request failed"), {
      status: response.status,
    });
  return result as T;
}

/** Compose only this service's authenticated artifact paths, never an external destination. */
function transport(path: string, method = "GET", body?: unknown) {
  return fetch((privateAccounts ? "/private/api/" : "/api/") + path, {
    method,
    credentials: "same-origin",
    cache: "no-store",
    redirect: "error",
    headers: privateAccounts
      ? { "Content-Type": "application/json", "X-PIMS-Request": "v1" }
      : {
          Authorization: "Bearer " + token,
          "Content-Type": "application/json",
        },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

/** Authorize one browser tab; no image/prompt data is placed in browser storage. */
export function connect(value: string): void {
  if (privateAccounts)
    throw new Error("Sign in to a local account instead of entering a token.");
  token = value.trim();
  sessionStorage.setItem("image-studio-token", token);
}

/** Issue a typed authenticated request and expose bounded server errors. */
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await transport(path, method, body);
  if (!response.ok) {
    const error = await response.json();
    if (privateAccounts && [401, 423].includes(response.status))
      location.reload();
    throw new Error(error.detail || "Request failed");
  }
  return response.json() as Promise<T>;
}

/** Download a private artifact using authorization, never a token query string. */
export async function download(path: string, name: string): Promise<void> {
  const response = await transport(path);
  if (!response.ok) throw new Error("Artifact download failed");
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Load an image as a private blob URL; the caller must revoke it on replacement. */
export async function imageUrl(identity: string): Promise<string> {
  const response = await transport(`images/${identity}/file`);
  if (!response.ok) throw new Error("Image preview failed");
  return URL.createObjectURL(await response.blob());
}

/** Convert a bounded user-selected raster to base64, without reading arbitrary local paths. */
export async function upload(file: File): Promise<unknown> {
  if (file.size > 5 * 1024 * 1024)
    throw new Error("Browser uploads are limited to 5 MiB");
  const data = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.onerror = () => reject(new Error("Unable to read selected file"));
    reader.readAsDataURL(file);
  });
  return api("images", "POST", { name: file.name, content: data });
}
