/** Private same-origin transport. Session tokens never accompany third-party requests. */
// Index: declarations connect@L17, api@L23, download@L44, imageUrl@L58, upload@L67; variables token@L3, value@L17, path@L24, method@L25, body@L26, response@L28, error@L37, path@L44, name@L44, response@L45, url@L49, link@L50, identity@L58, response@L59, file@L67, data@L70, resolve@L70, reject@L70, reader@L71. Purposes/parameters: docs/code-map.json.
let token =
  new URLSearchParams(location.hash.slice(1)).get("token") ||
  sessionStorage.getItem("image-studio-token") ||
  "";
if (location.hash.includes("token=")) {
  sessionStorage.setItem("image-studio-token", token);
  history.replaceState(null, "", location.pathname);
}
window.addEventListener("hashchange", () => {
  if (new URLSearchParams(location.hash.slice(1)).has("token"))
    location.reload();
});

/** Authorize one browser tab; no image/prompt data is placed in browser storage. */
export function connect(value: string): void {
  token = value.trim();
  sessionStorage.setItem("image-studio-token", token);
}

/** Issue a typed authenticated request and expose bounded server errors. */
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Request failed");
  }
  return response.json() as Promise<T>;
}

/** Download a private artifact using authorization, never a token query string. */
export async function download(path: string, name: string): Promise<void> {
  const response = await fetch(`/api/${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
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
  const response = await fetch(`/api/images/${identity}/file`, {
    headers: { Authorization: `Bearer ${token}` },
  });
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
