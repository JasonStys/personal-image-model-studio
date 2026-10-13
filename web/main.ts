/** Jason Stys: fail-closed mode selection; private accounts never fall back to developer bearer mode. */
// Index: declarations boot@L9; variables response@L11, health@L16, error@L28, app@L29, message@L31. Purposes/parameters: docs/code-map.json.
import "./style.css";
import { legacySession, privateMode } from "./api";
import { mountStudio } from "./workspace";
import { startPortal } from "./portal";

/** Select only the service's verified local mode before enabling any data transport. */
async function boot() {
  try {
    const response = await fetch("/health", {
      cache: "no-store",
      redirect: "error",
    });
    if (!response.ok) throw new Error("Local service is unavailable.");
    const health = await response.json();
    if (health.mode === "private-local-accounts") {
      privateMode();
      await startPortal();
    } else if (health.ready === true && !health.mode) {
      legacySession();
      mountStudio();
    } else {
      throw new Error(
        "Use the private-account launcher. Developer mode requires its explicit local session link.",
      );
    }
  } catch (error) {
    const app = document.querySelector("#app")!;
    app.className = "account-screen";
    const message = document.createElement("p");
    message.textContent =
      error instanceof Error
        ? error.message
        : "Unable to start the local studio.";
    app.replaceChildren(message);
  }
}
void boot();
