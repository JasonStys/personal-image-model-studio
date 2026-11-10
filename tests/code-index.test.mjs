/** Jason Stys: exercise the actual metadata CLI with disappearing and inaccessible output files. */
// Index: declarations fixture@L16, run@L35; variables repository@L10, parent@L17, directory@L19, name@L20, name@L26, directory@L35, code@L35, args@L36, preload@L38, code@L61, directory@L63, first@L65, output@L67, before@L68, result@L69. Purposes/parameters: docs/code-map.json.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";
import { test } from "node:test";

const repository = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);

/** Own only this temporary fixture tree; import the real checked-in CLI with existing locked tooling. */
function fixture() {
  const parent = path.join(repository, ".runtime");
  fs.mkdirSync(parent, { recursive: true });
  const directory = fs.mkdtempSync(path.join(parent, "index-regression-"));
  for (const name of ["studio", "scripts", "tests", "web"])
    fs.mkdirSync(path.join(directory, name));
  fs.copyFileSync(
    path.join(repository, "scripts/code_index.mjs"),
    path.join(directory, "scripts/code_index.mjs"),
  );
  for (const name of ["playwright.config.ts", "playwright.private.config.ts"])
    fs.writeFileSync(
      path.join(directory, name),
      "/** Synthetic index fixture. */\n// Index:\nexport const sample = 1;\n",
    );
  return directory;
}

/** Invoke a fresh bounded CLI process; the preload faults only the fixture's generated JSON read. */
function run(directory, code) {
  const args = [];
  if (code) {
    const preload = path.join(directory, "inject.mjs");
    fs.writeFileSync(
      preload,
      `import fs from 'node:fs';
const read = fs.readFileSync;
let injected = false;
fs.readFileSync = function(file, ...args) {
  if (!injected && String(file).replaceAll('\\\\', '/').endsWith('docs/code-map.json')) {
    injected = true;
    ${code === "ENOENT" ? "fs.unlinkSync(file);" : `throw Object.assign(new Error('Owned synthetic output failure'), { code: '${code}' });`}
  }
  return read.call(this, file, ...args);
};\n`,
    );
    args.push("--import", pathToFileURL(preload).href);
  }
  return spawnSync(process.execPath, [...args, "scripts/code_index.mjs"], {
    cwd: directory,
    encoding: "utf8",
    timeout: 15000,
  });
}

for (const code of ["ENOENT", "EACCES", "EIO"]) {
  test(`actual index CLI handles output ${code} without a check/read race`, () => {
    const directory = fixture();
    try {
      const first = run(directory);
      assert.equal(first.status, 0, first.stderr);
      const output = path.join(directory, "docs/code-map.json");
      const before = fs.readFileSync(output, "utf8");
      const result = run(directory, code);
      if (code === "ENOENT") {
        assert.equal(result.status, 0, result.stderr);
        assert.equal(fs.readFileSync(output, "utf8"), before);
      } else {
        assert.notEqual(result.status, 0);
        assert.match(result.stderr, /Owned synthetic output failure/);
        assert.equal(fs.readFileSync(output, "utf8"), before);
      }
    } finally {
      // Verify the resolved target before recursively removing only this test's fixture tree.
      assert.equal(
        path.dirname(path.resolve(directory)),
        path.join(repository, ".runtime"),
      );
      assert.ok(path.basename(directory).startsWith("index-regression-"));
      fs.rmSync(directory, { recursive: true, force: true });
    }
  });
}
