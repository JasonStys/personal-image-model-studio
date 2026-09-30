/** Structured browser workspace: explicit dataset/model/training/generation/feedback actions. */
// Index: declarations message@L58, act@L73, values@L97, form@L104, view@L119, options@L139, cards@L154, preview@L187, jobs@L202, refresh@L233; variables root@L7, workspace@L8, selectedImage@L9, currentUrl@L10, busy@L11, text@L58, failed@L58, target@L59, task@L73, controls@L77, previous@L80, button@L80, button@L81, error@L87, button@L91, index@L91, form@L97, key@L99, value@L99, id@L105, action@L106, value@L107, target@L108, target@L111, event@L112, name@L119, panel@L122, button@L125, button@L134, id@L140, items@L141, empty@L142, select@L144, before@L145, item@L148, option@L149, id@L155, items@L156, open@L157, identity@L157, target@L159, item@L161, card@L162, title@L164, detail@L167, button@L175, identity@L187, next@L188, image@L192, id@L202, target@L203, job@L205, card@L206, title@L208, status@L211, report@L214, cancel@L222, model@L241, model@L246, id@L249, identity@L258, selected@L260, input@L264, target@L265, item@L267, label@L268, input@L270, account@L280, runtime@L290, error@L296, value@L303, value@L307, subject@L308, value@L343, target@L343, value@L360, path@L365, value@L370, value@L371, value@L381, term@L385, value@L389, value@L394, result@L395, link@L400, value@L404, value@L410, value@L424, event@L437, file@L438, value@L442, form@L443, original@L444, image@L444. Purposes/parameters: docs/code-map.json.
import "./style.css";
import { api, connect, download, imageUrl, upload } from "./api";
import type { Workspace } from "./types";

const root = document.querySelector<HTMLDivElement>("#app")!;
let workspace: Workspace = { model: [], dataset: [], image: [], job: [] };
let selectedImage = "";
let currentUrl = "";
let busy = false;

/** Static trusted markup only. All server/user values are inserted through textContent/options. */
root.innerHTML = `
<aside><div class="brand">◈ <span>Personal Image<br>Model Studio</span></div><p>YOUR DATA. EXPLICIT CONTROL.</p>
<nav aria-label="Workspace"><button data-view="create" class="active">01 · Compose & generate</button><button data-view="data">02 · Datasets & glossary</button><button data-view="train">03 · Train & models</button><button data-view="history">04 · History & feedback</button><button data-view="method">05 · Method & limits</button></nav>
<footer>Local-first · Real checkpoints<br>No hidden retraining or uploads</footer></aside>
<main><header><div><p class="eyebrow">A CREATIVE WORKSPACE, NOT A BLACK BOX</p><h1 id="title">Compose & generate</h1></div><span class="pill">PRIVATE LOCAL SESSION</span></header>
<p id="message" role="status" aria-live="polite"></p>
<section id="authorization" hidden><h2>Connect to your local session</h2><form id="auth"><label>Session token<input name="token" type="password" required></label><button>Connect</button></form></section>
<div id="views">
<section data-panel="create"><div class="columns"><article><h2>Give every idea its own field</h2><p>Use any positive field. Numeric syntax: (blue:1.4). Learn what the selected model can express before judging results.</p>
<form id="generate"><label>Model<select name="model_id" id="generation-model" required></select></label>
<label>Scene description<textarea name="description" rows="3" placeholder="blue circle on white background"></textarea></label>
<div class="pair"><label>Art style<input name="style" placeholder="photography, watercolor…"></label><label>Scene tags<input name="tags" placeholder="light, composition, atmosphere…"></label></div>
<details><summary>Independent negative prompts</summary><label>Negative scene<textarea name="negative_description"></textarea></label><label>Negative style<input name="negative_style"></label><label>Negative tags<input name="negative_tags"></label></details>
<details><summary>Subject & placement</summary><label>Subject name (label only)<input name="subject_name"></label><label>Subject description<textarea name="subject_description"></textarea></label><label>Subject tags<input name="subject_tags"></label><label>Subject framing<input name="framing" placeholder="foreground, left side"></label><label>Subject negative<input name="subject_negative"></label><label>Region (native only; optional left,top,right,bottom)<input name="region" placeholder="0,0,0.5,1"></label></details>
<div class="triple"><label>Width<input name="width" type="number" min="32" max="1024" step="8" value="256"></label><label>Height<input name="height" type="number" min="32" max="1024" step="8" value="256"></label><label>Seed<input name="seed" type="number" min="0" max="2147483647" value="1337"></label></div>
<div class="triple"><label>Steps<input name="steps" type="number" min="1" max="100" value="50"></label><label>Guidance<input name="guidance" type="number" min="1" max="12" step="0.1" value="2"></label><label>Edit strength<input name="strength" type="number" min="0.01" max="1" step="0.01" value="0.6"></label></div>
<div class="pair"><label>Operation<select name="mode"><option value="text">Text to image</option><option value="edit">Image to image</option><option value="inpaint">Masked inpainting</option><option value="expand">Expand canvas / aspect ratio</option></select></label><label>Source image<select name="image_id" id="source-image"></select></label></div>
<label>Mask image (white edits, black preserves)<select name="mask_id" id="mask-image"></select></label>
<button class="primary">Generate with learned weights</button></form></article>
<article class="preview-card"><h2>Your canvas</h2><p id="preview-note">Select a completed image from history. Native examples are 32px learned models, displayed larger.</p><div class="canvas"><img id="preview" alt="Selected generated or uploaded artwork" hidden><div id="empty">◈<p>Your ideas, with provenance.</p></div></div><button id="download-image" disabled>Download PNG</button><label>Upload source image or mask<input id="upload" type="file" accept="image/png,image/jpeg,image/webp,image/bmp"></label><h3>Active jobs</h3><div id="create-jobs"></div></article></div></section>
<section data-panel="data" hidden><article><h2>Build a dataset you can audit</h2><p>Import image folders or ZIP files with same-stem UTF-8 .txt captions and optional .json metadata. Sources combine into one duplicate-aware dataset. Explicit AI-origin images are retained separately and excluded from ordinary training.</p><form id="import-dataset"><label>Dataset name<input name="name" required></label><label>Local folders / ZIP paths, one per line<textarea name="paths" rows="4" required></textarea></label><label class="check"><input name="rights" type="checkbox" required>I own or have permission to train on every selected source.</label><button>Import selected sources</button></form><button id="synthetic">Create owned synthetic test dataset</button><div id="datasets"></div></article><article><h2>Review tag meanings</h2><p>Definitions are operator reviewed, not guessed from a search. Stored inside the selected dataset; this version does not automatically train on glossary prose.</p><form id="glossary"><label>Dataset<select name="dataset" id="glossary-dataset"></select></label><label>Glossary entries JSON<textarea name="entries" rows="8" placeholder='{"rim light":{"definition":"Light from behind outlines a subject","source":"Your verified reference","reviewed":true}}'></textarea></label><button type="button" id="load-glossary">Load definitions</button><button>Save reviewed definitions</button></form></article></section>
<section data-panel="train" hidden><div class="columns"><article><h2>Train actual weights</h2><p>Fresh native models learn only your captions and pixels. Start small, inspect held-out metrics, then continue from a verified checkpoint. A short run is not a useful general image model.</p><form id="train"><label>Model name<input name="name" value="My custom model" required></label><fieldset><legend>Select datasets</legend><div id="training-datasets"></div></fieldset><label>Training mode<select name="mode"><option value="native">From-scratch native diffusion</option><option value="lora">Classic Stable Diffusion LoRA</option></select></label><label>LoRA base model<select name="base_model_id" id="base-model"></select></label><label>Resume native checkpoint<select name="resume_model_id" id="resume-model"></select></label><div class="triple"><label>Additional steps<input name="steps" type="number" min="1" max="10000" value="1000"></label><label>Resolution<select name="resolution"><option>32</option><option>64</option><option>128</option></select></label><label>Batch size<input name="batch_size" type="number" min="1" max="32" value="16"></label></div><div class="triple"><label>Learning rate<input name="learning_rate" type="number" min="0.000001" max="0.01" step="0.000001" value="0.001"></label><label>Device<select name="device"><option value="auto">Auto</option><option value="cuda">CUDA GPU</option><option value="cpu">CPU</option></select></label><label>Time limit (seconds)<input name="max_seconds" type="number" min="10" max="7200" value="1200"></label></div><label>Training seed<input name="seed" type="number" min="0" max="2147483647" value="1337"></label><button class="primary">Start bounded training</button></form></article><article><h2>Your model library</h2><div id="models"></div><h3>Register a local model</h3><form id="import-model"><label>Model label<input name="name" required></label><label>Local model directory<input name="path" required></label><label>Format<select name="kind"><option value="native">Image Studio native checkpoint</option><option value="diffusers">Classic Stable Diffusion (safe tensors)</option></select></label><label>License / authorization note<input name="license_note" required></label><button>Verify & register</button></form><p>No model is silently downloaded; incompatible model families fail explicitly.</p></article></div></section>
<section data-panel="history" hidden><div class="columns"><article><h2>Images & human feedback</h2><div id="images"></div><form id="feedback"><label>Image<select name="image" id="feedback-image"></select></label><label>Human score (-10 to 10)<input name="score" type="number" min="-10" max="10" value="0"></label><label>What went well<textarea name="good"></textarea></label><label>What to change<textarea name="change"></textarea></label><label>What to add<input name="add"></label><label>What to remove<input name="remove"></label><label class="check"><input name="allow_training" type="checkbox">Permit explicit feedback-dataset export for future training</label><button>Save human feedback</button><button type="button" id="revise">Use these notes for an explicit revision</button></form></article><article><h2>Run history & reports</h2><div id="history-jobs"></div></article></div></section>
<section data-panel="method" hidden><article><h2>What is real—and what is not promised</h2><p>Real native optimization, held-out denoising evaluation, safe checkpoint reload/resume, numeric text weights, region-conditioned native denoising, masked edits and centered aspect expansion are executable features.</p><p>The compact native model learns a capped word vocabulary from your training captions. It is not a general language model. Unknown/truncated words are reported. Enlarged outputs do not gain learned high-resolution detail. Regional denoising is experimental, not guaranteed character placement.</p><p>Classic Stable Diffusion directories and LoRA adapters use an explicitly supplied local model. No arbitrary model architecture, executable remote model code, cloud provisioning, universal website crawler, visual AI-origin detector or reliable semantic scene judge is claimed.</p><p>Website data should be exported through an authorized provider API/account and imported locally. Never enter account passwords here. Reviewed tag definitions are editable, not automatically researched in your logged-in browser. Feedback never silently triggers retraining or guarantees a score of 10.</p><form id="policy"><label>Optional blocked positive phrases, one per line<textarea name="denied_terms" rows="4"></textarea></label><button>Save local phrase policy</button></form><p>Phrase matching is transparent but not a comprehensive content-safety system. Supplied pretrained safety-checker results are respected.</p></article></section>
</div><footer class="page-footer">Source → reviewed dataset → learned model → reproducible artifact → human feedback</footer></main>`;

/** Surface status text safely; never render backend/user values as HTML. */
document.querySelector("[data-panel=data]")!.insertAdjacentHTML(
  "beforeend",
  `
<article><h2>Authorized DeviantArt connector</h2><p>Read-only access to your own gallery, not favourites or other artists. Passwords stay on DeviantArt. No import or training starts automatically.</p>
<p id="da-status">Not connected</p><form id="da-connect"><label>Registered public OAuth client ID<input name="client_id" inputmode="numeric" pattern="[0-9]{1,12}" required></label><p>Register a public PKCE application yourself and whitelist the callback shown below. Review the provider's developer terms and artwork permissions.</p><button>Prepare browser authorization</button></form>
<p id="da-callback"></p><a id="da-authorize" href="https://www.deviantart.com" target="_blank" rel="noreferrer" hidden>Continue authorization on DeviantArt</a>
<form id="da-import"><label>Gallery dataset name<input name="name" value="My authorized gallery" required></label><label>Maximum entries to inspect<input name="max_items" type="number" min="1" max="96" value="24"></label><label class="check"><input name="rights_confirmed" type="checkbox" required>I have training rights for every selected entry (account access alone does not grant rights).</label><label class="check"><input name="provider_terms_reviewed" type="checkbox" required>I have reviewed the provider terms and confirm this use is permitted.</label><button>Import bounded own-gallery sample</button></form>
<button id="da-disconnect">Forget this session's account connection</button><p>Explicit AI-origin content is quarantined. Known NoAI/opt-out flags are skipped. Unlabelled AI cannot be reliably identified. No credentials or account art belong in Git.</p></article>`,
);
document
  .querySelector("[data-panel=history] article")!
  .insertAdjacentHTML(
    "beforeend",
    `<button id="feedback-export">Download consenting feedback dataset</button><p>Exported generated images remain AI-labelled and excluded from ordinary training. This is not automatic reinforcement learning.</p>`,
  );

/** Surface status text safely; never render backend/user values as HTML. */
function message(text: string, failed = false): void {
  const target = document.querySelector<HTMLParagraphElement>("#message")!;
  target.textContent = text;
  target.classList.toggle("error", failed);
}

/** Trusted local-runtime setup markup; selected executables require an explicit trust acknowledgement. */
document
  .querySelector("[data-panel=method] article")!
  .insertAdjacentHTML(
    "beforeend",
    `<h3>Trusted local ML runtime</h3><p id="runtime-status"></p><form id="runtime-choice"><label>Installed ML Python executable<input name="python" placeholder="Path to your trusted ML environment's python.exe or python3" required></label><label class="check"><input name="trusted" type="checkbox" required>I trust this executable. Worker jobs will run it with the app's own modules.</label><button>Save runtime while idle</button></form><p>The portable shell includes the UI, not GPU drivers or ML dependencies. Install the documented ML environment once, then select it here.</p>`,
  );

/** Execute one explicit action and refresh metadata; prevent duplicate form submissions. */
async function act(task: () => Promise<unknown>): Promise<void> {
  if (busy) return;
  busy = true;
  message("Working…");
  const controls = Array.from(
    document.querySelectorAll<HTMLButtonElement>("button:not(#download-image)"),
  );
  const previous = controls.map((button) => button.disabled);
  controls.forEach((button) => (button.disabled = true));
  document.querySelector("main")!.setAttribute("aria-busy", "true");
  try {
    await task();
    message("Saved. Check job history for queued work.");
    await refresh();
  } catch (error) {
    message(error instanceof Error ? error.message : "Action failed", true);
  } finally {
    busy = false;
    controls.forEach((button, index) => (button.disabled = previous[index]));
    document.querySelector("main")!.setAttribute("aria-busy", "false");
  }
}

/** Read form values as plain strings; numeric/JSON interpretation remains explicit. */
function values(form: HTMLFormElement): Record<string, string> {
  return Object.fromEntries(
    Array.from(new FormData(form)).map(([key, value]) => [key, String(value)]),
  );
}

/** Bind a form to an explicit action without installing global delegated HTML handlers. */
function form(
  id: string,
  action: (
    value: Record<string, string>,
    target: HTMLFormElement,
  ) => Promise<unknown>,
): void {
  const target = document.querySelector<HTMLFormElement>(`#${id}`)!;
  target.addEventListener("submit", (event) => {
    event.preventDefault();
    void act(() => action(values(target), target));
  });
}

/** Switch visible workspace sections while preserving entered form values. */
function view(name: string): void {
  document
    .querySelectorAll<HTMLElement>("[data-panel]")
    .forEach((panel) => (panel.hidden = panel.dataset.panel !== name));
  document
    .querySelectorAll<HTMLButtonElement>("[data-view]")
    .forEach((button) =>
      button.classList.toggle("active", button.dataset.view === name),
    );
  document.querySelector("#title")!.textContent = document
    .querySelector<HTMLButtonElement>(`[data-view="${name}"]`)!
    .textContent!.slice(5);
}
document
  .querySelectorAll<HTMLButtonElement>("[data-view]")
  .forEach((button) =>
    button.addEventListener("click", () => view(button.dataset.view!)),
  );

/** Update selects without resetting an existing selection during background polling. */
function options(
  id: string,
  items: { id: string; name: string }[],
  empty = false,
): void {
  const select = document.querySelector<HTMLSelectElement>(`#${id}`)!;
  const before = select.value;
  select.replaceChildren();
  if (empty) select.add(new Option("None", ""));
  items.forEach((item) => select.add(new Option(item.name, item.id)));
  if (Array.from(select.options).some((option) => option.value === before))
    select.value = before;
}

/** Render metadata cards using safe text nodes and scoped controls. */
function cards(
  id: string,
  items: { name?: string; id: string; details?: unknown; counts?: unknown }[],
  open?: (identity: string) => void,
): void {
  const target = document.querySelector(`#${id}`)!;
  target.replaceChildren();
  items.forEach((item) => {
    const card = document.createElement("div");
    card.className = "record";
    const title = document.createElement("strong");
    title.textContent = item.name || item.id.slice(0, 8);
    card.append(title);
    const detail = document.createElement("pre");
    detail.textContent = JSON.stringify(
      item.counts || item.details || {},
      null,
      2,
    );
    card.append(detail);
    if (open) {
      const button = document.createElement("button");
      button.textContent = "Preview image";
      button.onclick = () => open(item.id);
      card.append(button);
    }
    target.append(card);
  });
  if (!items.length)
    target.textContent = "No records yet. Create or import your first one.";
}

/** Show a registered image and revoke the previous private blob to prevent browser memory leaks. */
async function preview(identity: string): Promise<void> {
  const next = await imageUrl(identity);
  if (currentUrl) URL.revokeObjectURL(currentUrl);
  currentUrl = next;
  selectedImage = identity;
  const image = document.querySelector<HTMLImageElement>("#preview")!;
  image.src = next;
  image.hidden = false;
  document.querySelector<HTMLElement>("#empty")!.hidden = true;
  document.querySelector<HTMLButtonElement>("#download-image")!.disabled =
    false;
  view("create");
}

/** Render cancellable job statuses/reports without retaining full worker logs in the browser. */
function jobs(id: string): void {
  const target = document.querySelector(`#${id}`)!;
  target.replaceChildren();
  workspace.job.slice(0, id === "create-jobs" ? 4 : 100).forEach((job) => {
    const card = document.createElement("div");
    card.className = "record";
    const title = document.createElement("strong");
    title.textContent = `${job.kind} · ${job.status}`;
    card.append(title);
    const status = document.createElement("p");
    status.textContent = job.error || JSON.stringify(job.progress);
    card.append(status);
    const report = document.createElement("button");
    report.textContent = "Download report";
    report.onclick = () =>
      void act(() => download(`jobs/${job.id}/report`, `job-${job.id}.json`));
    card.append(report);
    if (
      !["completed", "failed", "cancelled", "interrupted"].includes(job.status)
    ) {
      const cancel = document.createElement("button");
      cancel.textContent = "Cancel job";
      cancel.onclick = () =>
        void act(() => api(`jobs/${job.id}/cancel`, "POST"));
      card.append(cancel);
    }
    target.append(card);
  });
}

/** Poll bounded workspace metadata, preserving checked datasets and active form edits. */
async function refresh(): Promise<void> {
  try {
    workspace = await api<Workspace>("workspace");
    document.querySelector<HTMLElement>("#authorization")!.hidden = true;
    document.querySelector<HTMLElement>("#views")!.hidden = false;
    options("generation-model", workspace.model);
    options(
      "base-model",
      workspace.model.filter((model) => model.kind === "diffusers"),
      true,
    );
    options(
      "resume-model",
      workspace.model.filter((model) => model.kind === "native"),
      true,
    );
    ["source-image", "mask-image", "feedback-image"].forEach((id) =>
      options(id, workspace.image, true),
    );
    options("glossary-dataset", workspace.dataset);
    cards("datasets", workspace.dataset);
    cards("models", workspace.model);
    cards(
      "images",
      workspace.image,
      (identity) => void act(() => preview(identity)),
    );
    const selected = Array.from(
      document.querySelectorAll<HTMLInputElement>(
        "input[name=dataset_ids]:checked",
      ),
    ).map((input) => input.value);
    const target = document.querySelector("#training-datasets")!;
    target.replaceChildren();
    workspace.dataset.forEach((item) => {
      const label = document.createElement("label");
      label.className = "check";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.name = "dataset_ids";
      input.value = item.id;
      input.checked = selected.includes(item.id);
      label.append(input, document.createTextNode(item.name));
      target.append(label);
    });
    jobs("create-jobs");
    jobs("history-jobs");
    const account = await api<{
      connected: boolean;
      username: string | null;
      callback: string;
    }>("connectors/deviantart");
    document.querySelector("#da-status")!.textContent = account.connected
      ? `Connected to ${account.username} (memory-only session)`
      : "Not connected; reauthorize after restart or expiry";
    document.querySelector("#da-callback")!.textContent =
      `Exact callback: ${account.callback}`;
    const runtime = await api<{ python: string; configured: boolean }>(
      "runtime",
    );
    document.querySelector("#runtime-status")!.textContent = runtime.configured
      ? `Worker executable: ${runtime.python}`
      : "Choose an installed ML runtime to enable worker jobs.";
  } catch (error) {
    document.querySelector<HTMLElement>("#authorization")!.hidden = false;
    document.querySelector<HTMLElement>("#views")!.hidden = true;
    message(error instanceof Error ? error.message : "Unable to connect", true);
  }
}

form("auth", async (value) => {
  connect(value.token);
  await refresh();
});
form("generate", async (value) => {
  const subject =
    value.subject_description || value.subject_tags || value.framing
      ? [
          {
            name: value.subject_name,
            description: value.subject_description,
            tags: value.subject_tags,
            framing: value.framing,
            negative: value.subject_negative,
            region: value.region ? value.region.split(",").map(Number) : null,
          },
        ]
      : [];
  return api("generate", "POST", {
    model_id: value.model_id,
    prompt: {
      description: value.description,
      style: value.style,
      tags: value.tags,
      negative_description: value.negative_description,
      negative_style: value.negative_style,
      negative_tags: value.negative_tags,
      subjects: subject,
    },
    width: Number(value.width),
    height: Number(value.height),
    seed: Number(value.seed),
    steps: Number(value.steps),
    guidance: Number(value.guidance),
    mode: value.mode,
    strength: Number(value.strength),
    image_id: value.mode === "text" ? null : value.image_id || null,
    mask_id: value.mode === "inpaint" ? value.mask_id || null : null,
  });
});
form("train", async (value, target) =>
  api("train", "POST", {
    name: value.name,
    dataset_ids: new FormData(target).getAll("dataset_ids"),
    steps: Number(value.steps),
    resolution: Number(value.resolution),
    batch_size: Number(value.batch_size),
    learning_rate: Number(value.learning_rate),
    device: value.device,
    seed: Number(value.seed),
    max_seconds: Number(value.max_seconds),
    mode: value.mode,
    resume_model_id:
      value.mode === "native" ? value.resume_model_id || null : null,
    base_model_id: value.mode === "lora" ? value.base_model_id || null : null,
  }),
);
form("import-dataset", async (value) =>
  api("datasets", "POST", {
    name: value.name,
    paths: value.paths
      .split("\n")
      .map((path) => path.trim())
      .filter(Boolean),
    rights_confirmed: value.rights === "on",
  }),
);
form("import-model", async (value) => api("models", "POST", value));
form("feedback", async (value) =>
  api(`images/${value.image}/feedback`, "POST", {
    score: Number(value.score),
    good: value.good,
    change: value.change,
    add: value.add,
    remove: value.remove,
    allow_training: value.allow_training === "on",
  }),
);
form("policy", async (value) =>
  api("policy", "PUT", {
    denied_terms: value.denied_terms
      .split("\n")
      .map((term) => term.trim())
      .filter(Boolean),
  }),
);
form("glossary", async (value) =>
  api(`datasets/${value.dataset}/glossary`, "PUT", {
    entries: JSON.parse(value.entries),
  }),
);
form("da-connect", async (value) => {
  const result = await api<{ url: string }>(
    "connectors/deviantart/connect",
    "POST",
    value,
  );
  const link = document.querySelector<HTMLAnchorElement>("#da-authorize")!;
  link.href = result.url;
  link.hidden = false;
});
form("runtime-choice", async (value) =>
  api("runtime", "PUT", {
    python: value.python,
    trusted: value.trusted === "on",
  }),
);
form("da-import", async (value) =>
  api("connectors/deviantart/import", "POST", {
    name: value.name,
    max_items: Number(value.max_items),
    rights_confirmed: value.rights_confirmed === "on",
    provider_terms_reviewed: value.provider_terms_reviewed === "on",
  }),
);
document.querySelector<HTMLButtonElement>("#da-disconnect")!.onclick = () =>
  void act(() => api("connectors/deviantart/disconnect", "POST"));
document.querySelector<HTMLButtonElement>("#feedback-export")!.onclick = () =>
  void act(() => download("feedback/export", "feedback-data.zip"));
document.querySelector<HTMLButtonElement>("#load-glossary")!.onclick = () =>
  void act(async () => {
    const value = await api<{ entries: unknown }>(
      `datasets/${document.querySelector<HTMLSelectElement>("#glossary-dataset")!.value}/glossary`,
    );
    document.querySelector<HTMLTextAreaElement>(
      "textarea[name=entries]",
    )!.value = JSON.stringify(value.entries, null, 2);
  });
document.querySelector<HTMLButtonElement>("#synthetic")!.onclick = () =>
  void act(() => api("datasets/synthetic", "POST"));
document.querySelector<HTMLButtonElement>("#download-image")!.onclick = () =>
  void act(() =>
    download(`images/${selectedImage}/file`, `image-${selectedImage}.png`),
  );
document.querySelector<HTMLInputElement>("#upload")!.onchange = (event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (file) void act(() => upload(file));
};
document.querySelector<HTMLButtonElement>("#revise")!.onclick = () => {
  const value = values(document.querySelector<HTMLFormElement>("#feedback")!);
  const form = document.querySelector<HTMLFormElement>("#generate")!;
  const original = workspace.image.find((image) => image.id === value.image)
    ?.request as { prompt?: { description?: string } } | undefined;
  (form.elements.namedItem("description") as HTMLTextAreaElement).value = [
    original?.prompt?.description,
    value.change,
    value.add,
  ]
    .filter(Boolean)
    .join(", ");
  (
    form.elements.namedItem("negative_description") as HTMLTextAreaElement
  ).value = value.remove;
  (form.elements.namedItem("mode") as HTMLSelectElement).value = "edit";
  (form.elements.namedItem("image_id") as HTMLSelectElement).value =
    value.image;
  view("create");
  message(
    "Review these revision fields, then explicitly press Generate. No automatic retry or score is promised.",
  );
};
window.addEventListener("pagehide", () => {
  if (currentUrl) URL.revokeObjectURL(currentUrl);
});
void refresh();
setInterval(() => {
  if (!busy && document.visibilityState === "visible") void refresh();
}, 4000);
