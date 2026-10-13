/** Jason Stys: local login, independent encryption, help, explicit file picks and idle locking. */
// Index: declarations Status@L7, notice@L34, action@L43, field@L56, bind@L61, b64@L70, derive@L78, recovery@L112, signIn@L126, unlockScreen@L158, selectedFiles@L187, fileControls@L246, workspace@L281, load@L382, heartbeat@L397, startPortal@L412; variables status@L18, pending@L19, lastHuman@L20, lastHeartbeat@L21, app@L22, author@L23, help@L24, text@L34, error@L34, node@L35, task@L43, error@L48, form@L56, name@L56, id@L61, task@L61, form@L61, form@L62, event@L63, bytes@L70, text@L71, i@L72, phrase@L78, salt@L78, bytes@L83, material@L84, key@L92, c@L98, code@L112, mode@L126, title@L129, form@L136, result@L137, form@L167, salt@L168, key@L170, files@L187, model@L187, folder@L187, batch@L188, directory@L189, paths@L190, file@L191, relative@L193, started@L194, offset@L205, bytes@L213, chunk@L216, top@L226, target@L229, input@L230, path@L237, path@L239, model@L246, form@L247, path@L250, controls@L256, folder@L258, label@L259, input@L262, controls@L284, link@L333, form@L342, runtimeNote@L352, mode@L359, error@L385, force@L397, idle@L405, event@L414, next@L427. Purposes/parameters: docs/code-map.json.
import { account } from "./api";
import { mountStudio } from "./workspace";

/** Caller-only account metadata; never password, recovery code, key or image pixels. */
interface Status {
  alias: string;
  configured: boolean;
  unlocked: boolean;
  salt: string | null;
  engine_busy: boolean;
  recovery_pending: boolean;
  save_failed: boolean;
  idle_seconds: 600 | 1800 | 7200;
  embedded_cpu: boolean;
}
let status: Status | null = null;
let pending = false;
let lastHuman = Date.now();
let lastHeartbeat = 0;
const app = document.querySelector<HTMLDivElement>("#app")!;
const author = `<p class="creator">Made by Jason Stys · <a href="https://github.com/JasonStys" target="_blank" rel="noreferrer">GitHub</a> · <a href="https://www.linkedin.com/in/jason-stys-31b30b351/" target="_blank" rel="noreferrer">Contact on LinkedIn</a></p>`;
const help = `<details class="portal-help"><summary>Help, privacy & installation</summary>
<h3>Start creating</h3><ol><li>Create a local alias/login password; save the one-use recovery code privately.</li><li>Choose a different vault phrase: 20–256 characters, preferably six random words. It cannot be recovered.</li><li>In Datasets, create owned synthetic examples or select images and same-name captions/ZIPs you may train on.</li><li>In Train, select a dataset and start a short 32px native model. Check its held-out report. Short runs produce noise, not a capable general generator.</li><li>Select the learned model, enter a matching scene, generate, then open History to preview/export and give feedback.</li></ol>
<h3>Privacy boundary</h3><p>This is a local account service, not a public website. Passwords are scrypt hashes; locked archives use AES-256-GCM. Your browser derives the vault key and gives it to your trusted local ML service while unlocked. Training needs plaintext pixels/weights in a temporary workspace. OS administrators, malware, untrusted runtimes or modified app code can access active data. A crash may leave recovery files until the owner unlocks and locks again. Use device encryption and your own OS login.</p>
<p>No ads, analytics, external fonts, unsolicited popups, model downloads or outside AI API calls are installed. DeviantArt is optional and contacts the provider only after explicit authorization/actions; its permissions may exceed read-only. Locking disconnects it. Account access is not a training-rights grant. Browser extensions are outside the app's control.</p>
<h3>Saving and recovery</h3><p>Idle completed changes are encrypted automatically. Save snapshot requires finished jobs/uploads. Lock/sign out cancels this account's queued/running jobs, seals data and closes provider sessions. Default human-idle lock is ten minutes; explicitly select a longer limit for slow training. Polling does not renew it. Closing a page attempts a lock; crashes do not guarantee cleanup. If saving fails, preserve the recovery files and free disk space.</p>
<p>Login recovery changes the login password, not the vault phrase. PNG/report/feedback exports are plaintext. An encrypted archive alone does not restore login/key settings in this release: also back up the entire protected account data directory after stopping the app. Deletion removes live data, not old backups or disk sectors.</p>
<h3>Installation and limits</h3><p>The portable CPU application bundles the native diffusion engine and opens your browser: no Python/npm setup for native training/generation. Packages are unsigned; verify official release checksums and do not blindly bypass OS warnings. Source mode can use an explicitly configured trusted full ML runtime for classic Stable Diffusion/LoRA. No GPU driver or pretrained weights are included.</p>
<p>One account may unlock the local engine at a time. Limits: 8 GiB/20,000 workspace files, eight queued/running jobs, 8 MiB requests and 4 MiB upload chunks. Public hosting, native mobile packages, universal model compatibility, independent security certification and photorealistic quality are not claimed. Never send credentials or private artwork in a GitHub issue.</p></details>`;

/** Safe status text, never user/backend values interpreted as HTML. */
function notice(text: string, error = false) {
  const node = document.querySelector<HTMLElement>("#portal-status");
  if (node) {
    node.textContent = text;
    node.classList.toggle("error", error);
  }
}

/** Serialize explicit account actions and never log supplied credentials or keys. */
async function action(task: () => Promise<void>) {
  if (pending) return;
  pending = true;
  try {
    await task();
  } catch (error) {
    notice(error instanceof Error ? error.message : "Action failed", true);
  } finally {
    pending = false;
  }
}

/** Read values only from the submitted form. */
function field(form: HTMLFormElement, name: string) {
  return String(new FormData(form).get(name) || "");
}

/** Bind static trusted forms without inline handlers. */
function bind(id: string, task: (form: HTMLFormElement) => Promise<void>) {
  const form = document.querySelector<HTMLFormElement>("#" + id)!;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void action(() => task(form));
  });
}

/** Encode chunks without an unbounded spread/argument stack. */
function b64(bytes: Uint8Array) {
  let text = "";
  for (let i = 0; i < bytes.length; i += 8192)
    text += String.fromCharCode(...bytes.subarray(i, i + 8192));
  return btoa(text);
}

/** PBKDF2-HMAC-SHA256/600,000 in WebCrypto; derived key is sent only to the trusted loopback worker service. */
async function derive(phrase: string, salt: string) {
  if (phrase.length < 20 || phrase.length > 256)
    throw new Error(
      "Choose a different vault phrase of 20–256 characters, preferably six random words.",
    );
  const bytes = new TextEncoder().encode(phrase);
  const material = await crypto.subtle.importKey(
    "raw",
    bytes,
    "PBKDF2",
    false,
    ["deriveBits"],
  );
  bytes.fill(0);
  const key = new Uint8Array(
    await crypto.subtle.deriveBits(
      {
        name: "PBKDF2",
        hash: "SHA-256",
        iterations: 600000,
        salt: Uint8Array.from(atob(salt), (c) => c.charCodeAt(0)),
      },
      material,
      256,
    ),
  );
  try {
    return b64(key);
  } finally {
    key.fill(0);
  }
}

/** Show the once-returned recovery result until the user acknowledges saving it privately. */
function recovery(code: string) {
  app.className = "account-screen";
  app.innerHTML = `<main class="portal-card"><h1>Save your login recovery code</h1><p>Keep this privately. It cannot recover a forgotten vault phrase.</p><code id="recovery-code"></code><button id="saved-recovery">I saved it privately</button>${author}${help}</main>`;
  document.querySelector("#recovery-code")!.textContent = code;
  document.querySelector("#saved-recovery")!.addEventListener(
    "click",
    () =>
      void action(async () => {
        await load();
      }),
  );
}

/** Real login/registration/recovery; no seeded accounts or default credentials. */
function signIn(mode: "login" | "register" | "reset" = "login") {
  status = null;
  app.className = "account-screen";
  const title =
    mode === "register"
      ? "Create your local account"
      : mode === "reset"
        ? "Recover your login"
        : "Sign in to your local studio";
  app.innerHTML = `<main class="portal-card"><p class="eyebrow">YOUR IMAGES. YOUR LOCAL ENGINE.</p><h1>Personal Image Model Studio</h1><h2>${title}</h2><p>This account belongs to this local installation. No public host or tracking.</p><p id="portal-status" role="status" aria-live="polite"></p><form id="portal-auth"><label>Account alias<input name="alias" autocomplete="username" pattern="[a-z0-9_][a-z0-9_-]{2,39}" minlength="3" maxlength="40" required></label><label>${mode === "reset" ? "New login password" : "Login password"}<input name="password" type="password" autocomplete="${mode === "login" ? "current-password" : "new-password"}" minlength="15" maxlength="128" required></label>${mode === "reset" ? '<label>Login recovery code<input name="recovery" type="password" autocomplete="off" minlength="32" maxlength="128" required></label>' : ""}<button class="primary">${mode === "register" ? "Register account" : mode === "reset" ? "Reset login" : "Sign in securely"}</button></form><div class="portal-buttons"><button id="login-mode">Sign in</button><button id="register-mode">Create account</button><button id="reset-mode">Recover login</button></div>${author}${help}</main>`;
  bind("portal-auth", async (form) => {
    const result = await account<{ recovery?: string }>(mode, "POST", {
      alias: field(form, "alias"),
      password: field(form, "password"),
      ...(mode === "reset" ? { recovery: field(form, "recovery") } : {}),
    });
    form.reset();
    if (result.recovery) recovery(result.recovery);
    else await load();
  });
  document
    .querySelector("#login-mode")!
    .addEventListener("click", () => signIn());
  document
    .querySelector("#register-mode")!
    .addEventListener("click", () => signIn("register"));
  document
    .querySelector("#reset-mode")!
    .addEventListener("click", () => signIn("reset"));
}

/** Independent document/model encryption phrase; not the login recovery mechanism. */
function unlockScreen() {
  app.className = "account-screen";
  app.innerHTML = `<main class="portal-card"><h1>Unlock your private image workspace</h1><p id="account-alias"></p><p>Use a different vault phrase. Its key is available to your trusted local worker while unlocked.</p><p id="portal-status" role="status" aria-live="polite"></p><form id="portal-unlock"><label>Vault phrase<input name="phrase" type="password" autocomplete="off" minlength="20" maxlength="256" required></label><button class="primary">Unlock or create workspace</button></form><button id="portal-signout">Sign out</button>${author}${help}</main>`;
  document.querySelector("#account-alias")!.textContent =
    "Local account: " + status!.alias;
  if (status!.engine_busy || status!.recovery_pending)
    notice(
      "An account may need to lock or recover its interrupted workspace first. No other account data is shown.",
    );
  bind("portal-unlock", async (form) => {
    const salt =
      status!.salt || b64(crypto.getRandomValues(new Uint8Array(16)));
    const key = await derive(field(form, "phrase"), salt);
    await account("unlock", "POST", { key, salt });
    form.reset();
    lastHuman = Date.now();
    await load();
  });
  document.querySelector("#portal-signout")!.addEventListener(
    "click",
    () =>
      void action(async () => {
        await account("logout", "POST");
        location.reload();
      }),
  );
}

/** Ordered, bounded file chunks; the file picker, not a typed PC path, grants selection. */
async function selectedFiles(files: FileList, model: boolean, folder: boolean) {
  let batch: string | undefined;
  let directory = "";
  const paths: string[] = [];
  for (const file of Array.from(files)) {
    if (!file.size) continue;
    const relative = folder ? file.webkitRelativePath : file.name;
    const started = await account<{
      id: string;
      batch: string;
      directory: string;
    }>("files", "POST", {
      path: relative,
      size: file.size,
      ...(batch ? { batch } : {}),
    });
    batch = started.batch;
    directory = started.directory;
    for (let offset = 0; offset < file.size; offset += 4 * 1024 * 1024) {
      notice(
        "Uploading " +
          file.name +
          " · " +
          Math.floor((offset / file.size) * 100) +
          "%",
      );
      const bytes = new Uint8Array(
        await file.slice(offset, offset + 4 * 1024 * 1024).arrayBuffer(),
      );
      const chunk = await account<{ complete: boolean; path: string | null }>(
        "files/" + started.id,
        "PUT",
        { offset, content: b64(bytes) },
      );
      if (chunk.complete && chunk.path) paths.push(chunk.path);
    }
  }
  if (!paths.length)
    throw new Error("Select at least one non-empty permitted file.");
  const top = folder
    ? Array.from(files)[0].webkitRelativePath.split("/")[0]
    : "";
  const target = directory + (top ? "/" + top : "");
  const input = document.querySelector<HTMLInputElement | HTMLTextAreaElement>(
    model
      ? "#import-model input[name=path]"
      : "#import-dataset textarea[name=paths]",
  )!;
  input.value = model
    ? target
    : folder || !paths.some((path) => path.endsWith(".zip"))
      ? target
      : paths.filter((path) => path.endsWith(".zip")).join("\n");
  notice(
    "Files staged privately. Review label, format and training rights, then explicitly import/register.",
  );
}

/** Replace arbitrary-path input capability with browser-selected account-scoped staging. */
function fileControls(model: boolean) {
  const form = document.querySelector<HTMLFormElement>(
    model ? "#import-model" : "#import-dataset",
  )!;
  const path = form.querySelector<HTMLInputElement | HTMLTextAreaElement>(
    model ? "[name=path]" : "[name=paths]",
  )!;
  path.readOnly = true;
  path.placeholder =
    "Choose files below; the app supplies an account-scoped location.";
  const controls = document.createElement("div");
  controls.className = "portal-file-controls";
  for (const folder of [false, true]) {
    const label = document.createElement("label");
    label.textContent =
      (model ? "Model" : "Dataset") + (folder ? " directory" : " files / ZIP");
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    if (folder) input.setAttribute("webkitdirectory", "");
    else
      input.accept = model
        ? ".safetensors,.json,.txt"
        : ".zip,.png,.jpg,.jpeg,.webp,.bmp,.txt,.json,.jsonl,.csv";
    input.addEventListener("change", () => {
      if (input.files)
        void action(() => selectedFiles(input.files!, model, folder));
    });
    label.append(input);
    controls.append(label);
  }
  form.prepend(controls);
}

/** Mount the actual ML UI only after unlock, with account controls/help and author contact. */
function workspace() {
  app.className = "";
  mountStudio(true);
  const controls = document.createElement("section");
  controls.id = "account-controls";
  controls.setAttribute("aria-label", "Account controls");
  controls.innerHTML = `<div class="portal-toolbar"><strong id="signed-alias"></strong><button id="lock-vault">Lock workspace</button><button id="save-vault">Save snapshot</button><button id="backup-vault">Download encrypted archive</button><button id="signout-vault">Sign out</button><label>Human-idle lock<select id="idle-setting"><option value="600">10 minutes</option><option value="1800">30 minutes</option><option value="7200">2 hours — long training</option></select></label></div><p id="portal-status" role="status" aria-live="polite"></p>${author}${help}<details><summary>Delete local account</summary><p>Removes live data, not old backups or disk sectors.</p><form id="delete-account"><label>Current login password<input name="password" type="password" autocomplete="current-password" minlength="15" maxlength="128" required></label><label class="check"><input name="confirm" type="checkbox" required>I backed up what I need and approve permanent deletion of this local account.</label><button>Delete my local account</button></form></details>`;
  app.before(controls);
  document.querySelector("#signed-alias")!.textContent =
    "Local account: " + status!.alias;
  document.querySelector<HTMLSelectElement>("#idle-setting")!.value = String(
    status!.idle_seconds,
  );
  document.querySelector("#idle-setting")!.addEventListener(
    "change",
    () =>
      void action(async () => {
        await heartbeat(true);
      }),
  );
  document.querySelector("#lock-vault")!.addEventListener(
    "click",
    () =>
      void action(async () => {
        notice("Cancelling owned jobs and sealing data…");
        await account("lock", "POST");
        location.reload();
      }),
  );
  document.querySelector("#signout-vault")!.addEventListener(
    "click",
    () =>
      void action(async () => {
        await account("logout", "POST");
        location.reload();
      }),
  );
  document.querySelector("#save-vault")!.addEventListener(
    "click",
    () =>
      void action(async () => {
        await account("save", "POST");
        notice("Encrypted snapshot saved.");
      }),
  );
  document.querySelector("#backup-vault")!.addEventListener(
    "click",
    () =>
      void action(async () => {
        await account("save", "POST");
        // Native browser attachment streaming avoids buffering an 8-GiB vault
        // into a JavaScript Blob. The HttpOnly cookie authenticates this URL.
        const link = document.createElement("a");
        link.href = "/private/backup";
        link.download = "private-workspace.pimsvault";
        link.click();
        notice(
          "Archive exported. Also back up the protected account directory/key settings after stopping the app.",
        );
      }),
  );
  bind("delete-account", async (form) => {
    await account("delete", "POST", {
      password: field(form, "password"),
      confirm: new FormData(form).has("confirm"),
    });
    location.reload();
  });
  fileControls(false);
  fileControls(true);
  document.querySelector("#runtime-choice")!.remove();
  const runtimeNote = document
    .querySelector("#runtime-status")!
    .parentElement!.querySelector("form + p");
  if (runtimeNote)
    runtimeNote.textContent =
      "The portable CPU app includes native training/generation. Account mode cannot change executable paths. An explicitly trusted full runtime can be selected only in the launcher for classic SD/LoRA.";
  if (status!.embedded_cpu) {
    const mode = document.querySelector<HTMLSelectElement>(
      "#train select[name=mode]",
    )!;
    mode.value = "native";
    mode.querySelector<HTMLOptionElement>("[value=lora]")!.disabled = true;
    document.querySelector<HTMLOptionElement>(
      "#import-model option[value=diffusers]",
    )!.disabled = true;
    document.querySelector<HTMLOptionElement>(
      "#train select[name=device] option[value=cuda]",
    )!.disabled = true;
    document.querySelector<HTMLSelectElement>(
      "#train select[name=device]",
    )!.value = "cpu";
  }
  if (status!.save_failed)
    notice(
      "A previous snapshot failed. Preserve files, check disk space, then retry Save/Lock.",
      true,
    );
}

/** Restore only account metadata from the server, never secrets from local/session storage. */
async function load() {
  try {
    status = await account<Status>("account");
  } catch (error) {
    if ((error as { status?: number }).status === 401) {
      signIn();
      return;
    }
    throw error;
  }
  if (status.unlocked) workspace();
  else unlockScreen();
}

/** Actual human input renews the timeout; background polling alone never does. */
async function heartbeat(force = false) {
  if (
    !status?.unlocked ||
    (!force && Date.now() - lastHeartbeat < 30000) ||
    Date.now() - lastHuman > 600000
  )
    return;
  lastHeartbeat = Date.now();
  const idle = Number(
    document.querySelector<HTMLSelectElement>("#idle-setting")?.value || 600,
  );
  await account("activity", "POST", { idle_seconds: idle });
}

/** Account startup and server-lock synchronization; reload drops prior plaintext DOM/blob references. */
export async function startPortal() {
  await load();
  for (const event of ["pointerdown", "keydown", "input"])
    document.addEventListener(
      event,
      () => {
        lastHuman = Date.now();
        void heartbeat().catch(() => undefined);
      },
      { passive: true },
    );
  setInterval(() => {
    if (!status?.unlocked || pending || document.visibilityState !== "visible")
      return;
    void account<Status>("account")
      .then((next) => {
        if (!next.unlocked) location.reload();
        else if (next.save_failed)
          notice(
            "Snapshot failed; preserve data, check disk space and retry Save.",
            true,
          );
      })
      .catch(() => location.reload());
  }, 4000);
  window.addEventListener("pagehide", () => {
    if (status?.unlocked)
      void fetch("/private/lock", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-PIMS-Request": "v1" },
        body: "{}",
        keepalive: true,
      }).catch(() => undefined);
  });
}
