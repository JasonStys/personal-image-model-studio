/** Structured browser workspace: explicit dataset/model/training/generation/feedback actions. */
// Index: declarations mountStudio@L15, clearDatasetReview@L63, renderDatasetReview@L76, message@L203, act@L218, values@L244, form@L254, view@L269, options@L289, cards@L304, preview@L337, jobs@L352, refresh@L385; variables accountMode@L15, root@L16, workspace@L17, selectedImage@L18, currentUrl@L19, busy@L20, datasetReview@L21, reviewGeneration@L22, reviewImageUrls@L23, url@L65, report@L76, datasetId@L76, target@L77, heading@L79, identity@L82, counts@L86, key@L88, count@L88, label@L89, value@L91, origin@L96, name@L98, count@L98, eligibility@L101, scope@L106, errors@L109, errorList@L112, error@L113, item@L114, candidates@L119, explanation@L122, pairs@L125, pair@L126, item@L127, button@L129, preview@L132, generation@L135, results@L137, result@L142, index@L148, result@L149, image@L152, unavailable@L159, empty@L171, limits@L176, text@L177, item@L178, text@L203, failed@L203, target@L204, task@L218, controls@L222, previous@L227, button@L227, button@L228, error@L234, button@L238, index@L238, form@L244, key@L246, value@L246, id@L255, action@L256, value@L257, target@L258, target@L261, event@L262, name@L269, panel@L272, button@L275, button@L284, id@L290, items@L291, empty@L292, select@L294, before@L295, item@L298, option@L299, id@L305, items@L306, open@L307, identity@L307, target@L309, item@L311, card@L312, title@L314, detail@L317, button@L325, identity@L337, next@L338, image@L342, id@L352, target@L353, job@L355, card@L356, title@L358, status@L361, report@L364, cancel@L374, model@L393, model@L398, id@L401, identity@L411, selected@L413, input@L417, target@L418, item@L420, label@L421, input@L423, account@L433, runtime@L443, error@L450, value@L461, value@L465, subject@L466, value@L501, target@L501, value@L518, path@L523, value@L528, value@L529, value@L539, term@L543, value@L547, value@L552, result@L553, link@L558, value@L562, value@L568, value@L582, value@L591, generation@L593, result@L594, url@L613, link@L618, event@L630, file@L631, value@L635, form@L636, original@L637, image@L637, url@L659. Purposes/parameters: docs/code-map.json.
import "./style.css";
import {
  api,
  connect,
  download,
  imageUrl,
  upload,
  datasetImageUrl,
} from "./api";
import type { DatasetReview, Workspace } from "./types";

/** Mount genuine ML controls only after private account unlock or an explicit developer session. */
export function mountStudio(accountMode = false) {
  const root = document.querySelector<HTMLDivElement>("#app")!;
  let workspace: Workspace = { model: [], dataset: [], image: [], job: [] };
  let selectedImage = "";
  let currentUrl = "";
  let busy = false;
  let datasetReview: DatasetReview | null = null;
  let reviewGeneration = 0;
  let reviewImageUrls: string[] = [];

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

  /** Trusted review controls; dataset names and evidence below are always text nodes. */
  document.querySelector("[data-panel=data]")!.insertAdjacentHTML(
    "beforeend",
    `
<article><h2>Review dataset quality before training</h2><p>Inspect caption and provenance gaps, eligible train/validation counts and a bounded sample of file integrity and cross-split visual similarity. Review is read-only: nothing is trained, relabelled or moved.</p>
<form id="dataset-review-form"><label for="review-dataset">Dataset to review</label><select id="review-dataset" name="dataset" required></select><button>Review dataset quality</button></form>
<button id="download-dataset-review" disabled>Download reviewed dataset report</button>
<section id="dataset-review-result" role="region" aria-label="Dataset quality review"><p>Select a dataset, then review it. No report is available yet.</p></section></article>`,
  );

  /** Replace the visible report with explicit empty/changed state, dropping the old export reference. */
  function clearDatasetReview(): void {
    datasetReview = null;
    reviewImageUrls.forEach((url) => URL.revokeObjectURL(url));
    reviewImageUrls = [];
    ++reviewGeneration;
    document.querySelector("#dataset-review-result")!.textContent =
      "Selection changed. Review this dataset before exporting its report.";
    document.querySelector<HTMLButtonElement>(
      "#download-dataset-review",
    )!.disabled = true;
  }

  /** Render provenance and similarity evidence without deriving a model quality score or injecting HTML. */
  function renderDatasetReview(report: DatasetReview, datasetId: string): void {
    const target = document.querySelector("#dataset-review-result")!;
    target.replaceChildren();
    const heading = document.createElement("h3");
    heading.textContent = "Read-only dataset review";
    target.append(heading);
    const identity = document.createElement("p");
    identity.className = "review-fingerprint";
    identity.textContent = `Dataset SHA-256: ${report.dataset_fingerprint} · Report SHA-256: ${report.report_sha256}`;
    target.append(identity);
    const counts = document.createElement("dl");
    counts.className = "review-counts";
    for (const [key, count] of Object.entries(report.counts)) {
      const label = document.createElement("dt");
      label.textContent = key.replaceAll("_", " ");
      const value = document.createElement("dd");
      value.textContent = String(count);
      counts.append(label, value);
    }
    target.append(counts);
    const origin = document.createElement("p");
    origin.textContent = `Declared origins: ${Object.entries(report.origins)
      .map(([name, count]) => `${name}: ${count}`)
      .join("; ")}`;
    target.append(origin);
    const eligibility = document.createElement("p");
    eligibility.textContent = report.minimum_training_counts_met
      ? "Minimum training counts met. This does not establish dataset or model quality."
      : "Not enough eligible data: native training needs at least 8 training and 2 validation examples.";
    target.append(eligibility);
    const scope = document.createElement("p");
    scope.textContent = `Verified ${report.inspection.verified_images} images; ${report.inspection.remaining_eligible_not_verified} eligible images not verified. Maximum ${report.inspection.maximum_images} images / ${report.inspection.maximum_file_bytes} file bytes / ${report.inspection.maximum_pixels} decoded pixels. ${report.inspection.cross_split_comparisons} cross-split comparisons. ${report.inspection.budget_stopped ? "Byte or pixel budget stopped inspection." : "Image sample limit applies."}`;
    target.append(scope);
    const errors = document.createElement("p");
    errors.textContent = `${report.inspection.integrity_errors.length} sampled file integrity errors.`;
    target.append(errors);
    const errorList = document.createElement("ul");
    for (const error of report.inspection.integrity_errors) {
      const item = document.createElement("li");
      item.textContent = `${error.name} (${error.hash}): ${error.reason}`;
      errorList.append(item);
    }
    target.append(errorList);
    const candidates = document.createElement("h4");
    candidates.textContent = `Near-duplicate candidates: ${report.candidate_pairs_total}`;
    target.append(candidates);
    const explanation = document.createElement("p");
    explanation.textContent = `These are review candidates, not proven duplicates or leakage. ${report.method}. ${report.candidate_pairs_not_shown} candidate pairs not shown.`;
    target.append(explanation);
    const pairs = document.createElement("ol");
    for (const pair of report.near_duplicate_candidates) {
      const item = document.createElement("li");
      item.textContent = `${pair.left.name} [${pair.left.split}, ${pair.left.hash}] ↔ ${pair.right.name} [${pair.right.split}, ${pair.right.hash}]: ${pair.difference_bits} different bits`;
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Preview candidate pair";
      const preview = document.createElement("div");
      preview.className = "dataset-pair-preview";
      button.onclick = async () => {
        const generation = reviewGeneration;
        button.disabled = true;
        const results = await Promise.allSettled([
          datasetImageUrl(datasetId, pair.left.hash),
          datasetImageUrl(datasetId, pair.right.hash),
        ]);
        if (generation !== reviewGeneration) {
          for (const result of results)
            if (result.status === "fulfilled")
              URL.revokeObjectURL(result.value);
          return;
        }
        preview.replaceChildren();
        for (let index = 0; index < results.length; index++) {
          const result = results[index];
          if (result.status === "fulfilled") {
            reviewImageUrls.push(result.value);
            const image = document.createElement("img");
            image.src = result.value;
            image.alt = `${index === 0 ? pair.left.split : pair.right.split} candidate ${index === 0 ? pair.left.name : pair.right.name}`;
            image.width = 192;
            image.height = 192;
            preview.append(image);
          } else {
            const unavailable = document.createElement("p");
            unavailable.textContent =
              "Candidate preview unavailable: source integrity or account access changed. Review again before training.";
            preview.append(unavailable);
          }
        }
      };
      item.append(button, preview);
      pairs.append(item);
    }
    target.append(pairs);
    if (!report.near_duplicate_candidates.length) {
      const empty = document.createElement("p");
      empty.textContent =
        "No candidates in the verified sample; remaining images were not checked.";
      target.append(empty);
    }
    const limits = document.createElement("ul");
    for (const text of report.limitations) {
      const item = document.createElement("li");
      item.textContent = text;
      limits.append(item);
    }
    target.append(limits);
  }

  /** Surface status text safely; never render backend/user values as HTML. */
  document.querySelector("[data-panel=data]")!.insertAdjacentHTML(
    "beforeend",
    `
<article><h2>Authorized DeviantArt connector</h2><p>The connector only reads your own gallery, not favourites or other artists. Passwords stay on DeviantArt. No import or training starts automatically.</p><p><strong>Permission warning:</strong> the provider consent screen may also advertise access to use and manage Sta.sh. The token grant can be broader than this app's read-only operations. Review the actual consent text and decline unless you accept every listed permission.</p>
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
      document.querySelectorAll<HTMLButtonElement>(
        "button:not(#download-image):not(#download-dataset-review)",
      ),
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
      Array.from(new FormData(form)).map(([key, value]) => [
        key,
        String(value),
      ]),
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
        !["completed", "failed", "cancelled", "interrupted"].includes(
          job.status,
        )
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
      options("review-dataset", workspace.dataset);
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
      document.querySelector("#runtime-status")!.textContent =
        runtime.configured
          ? `Worker executable: ${runtime.python}`
          : "Choose an installed ML runtime to enable worker jobs.";
    } catch (error) {
      document.querySelector<HTMLElement>("#authorization")!.hidden =
        accountMode;
      document.querySelector<HTMLElement>("#views")!.hidden = true;
      message(
        error instanceof Error ? error.message : "Unable to connect",
        true,
      );
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
  document.querySelector<HTMLSelectElement>("#review-dataset")!.onchange =
    clearDatasetReview;
  form("dataset-review-form", async (value) => {
    clearDatasetReview();
    const generation = reviewGeneration;
    const result = await api<DatasetReview>(`datasets/${value.dataset}/review`);
    if (
      generation !== reviewGeneration ||
      document.querySelector<HTMLSelectElement>("#review-dataset")!.value !==
        value.dataset
    )
      throw new Error(
        "Dataset selection changed. Review the selected dataset again.",
      );
    datasetReview = result;
    renderDatasetReview(result, value.dataset);
    document.querySelector<HTMLButtonElement>(
      "#download-dataset-review",
    )!.disabled = false;
  });
  document.querySelector<HTMLButtonElement>(
    "#download-dataset-review",
  )!.onclick = () => {
    if (!datasetReview) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(datasetReview, null, 2) + "\n"], {
        type: "application/json",
      }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `dataset-review-${datasetReview.dataset_fingerprint.slice(0, 12)}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
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
    reviewImageUrls.forEach((url) => URL.revokeObjectURL(url));
  });
  void refresh();
  setInterval(() => {
    if (!busy && document.visibilityState === "visible") void refresh();
  }, 4000);
}
