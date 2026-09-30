/** Regenerate/check exact AST source indexes; file edits are bulk mechanical metadata updates only. */
// Index: declarations walk@L30, inventory@L44, visit@L58, names@L80, publish@L108; variables root@L8, check@L9, python@L10, files@L19, file@L26, directory@L30, entry@L33, file@L40, file@L44, source@L44, result@L46, tree@L53, declarations@L54, variables@L55, line@L56, node@L56, node@L58, comments@L66, comment@L73, comment@L74, identifiers@L79, name@L80, element@L83, name@L88, file@L108, text@L108, previous@L109, maps@L121, file@L122, source@L123, marker@L124, line@L125, lines@L127, result@L132, header@L133, value@L133, value@L133, line@L138. Purposes/parameters: docs/code-map.json.
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import ts from "typescript";

const root = process.cwd();
const check = process.argv.includes("--check");
const python =
  process.env.IMAGE_STUDIO_TEST_PYTHON ||
  (fs.existsSync(path.join(root, ".venv"))
    ? path.join(
        root,
        ".venv",
        process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
      )
    : "python");
const files = [
  ...walk("studio"),
  ...walk("scripts"),
  ...walk("tests"),
  ...walk("web"),
  "playwright.config.ts",
]
  .filter((file) => /\.(py|ts|mjs)$/.test(file))
  .sort();

/** Enumerate only checked-in source folders, never caches, private data, dependencies or model weights. */
function walk(directory) {
  return fs
    .readdirSync(directory, { withFileTypes: true })
    .flatMap((entry) =>
      entry.name.startsWith("__") && entry.isDirectory()
        ? []
        : entry.isDirectory()
          ? walk(path.join(directory, entry.name))
          : [path.join(directory, entry.name)],
    )
    .map((file) => file.replaceAll("\\", "/"));
}

/** Read Python AST or TypeScript compiler AST; inventory generation never executes a source module. */
function inventory(file, source) {
  if (file.endsWith(".py")) {
    const result = spawnSync(python, ["scripts/python_index.py", file], {
      encoding: "utf8",
    });
    if (result.status !== 0)
      throw new Error(result.stderr || "Python index failed");
    return JSON.parse(result.stdout);
  }
  const tree = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true);
  const declarations = [],
    variables = [];
  const line = (node) =>
    tree.getLineAndCharacterOfPosition(node.getStart(tree)).line + 1;
  function visit(node) {
    if (
      (ts.isFunctionDeclaration(node) ||
        ts.isClassDeclaration(node) ||
        ts.isInterfaceDeclaration(node) ||
        ts.isTypeAliasDeclaration(node)) &&
      node.name
    ) {
      const comments = ts.getLeadingCommentRanges(source, node.pos) || [];
      declarations.push({
        name: node.name.text,
        line: line(node.name),
        kind: ts.SyntaxKind[node.kind],
        purpose:
          comments
            .map((comment) => source.slice(comment.pos, comment.end))
            .filter((comment) => !comment.startsWith("// Index:"))
            .join(" ") || node.getText(tree).slice(0, 180),
      });
    }
    if (ts.isVariableDeclaration(node) || ts.isParameter(node)) {
      const identifiers = [];
      function names(name) {
        if (ts.isIdentifier(name)) identifiers.push(name);
        else if (ts.isBindingPattern(name))
          name.elements.forEach((element) => {
            if (ts.isBindingElement(element)) names(element.name);
          });
      }
      names(node.name);
      identifiers.forEach((name) =>
        variables.push({
          name: name.text,
          line: line(name),
          kind: ts.isParameter(node) ? "parameter" : "variable",
          purpose: node.getText(tree).slice(0, 180),
        }),
      );
    }
    ts.forEachChild(node, visit);
  }
  visit(tree);
  return {
    purpose: source.match(/^\/\*\*?([\s\S]*?)\*\//)?.[1].trim() || "",
    declarations,
    variables,
  };
}

/** Compare mechanical outputs or publish them; no nondeterministic timestamps/machine paths enter docs. */
function publish(file, text) {
  const previous = fs.existsSync(file)
    ? fs.readFileSync(file, "utf8").replaceAll("\r\n", "\n")
    : "";
  if (previous === text) return;
  if (check)
    throw new Error(
      `Stale generated metadata: ${file}; run node scripts/code_index.mjs`,
    );
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, text);
}

const maps = {};
for (const file of files) {
  let source = fs.readFileSync(file, "utf8").replaceAll("\r\n", "\n");
  const marker = file.endsWith(".py") ? "# Index:" : "// Index:";
  if (!source.split("\n").some((line) => line.startsWith(marker))) {
    if (check) throw new Error(`Missing index header: ${file}`);
    const lines = source.split("\n");
    lines.splice(1, 0, marker);
    source = lines.join("\n");
    fs.writeFileSync(file, source);
  }
  const result = inventory(file, source);
  const header = `${marker} declarations ${result.declarations.map((value) => `${value.name}@L${value.line}`).join(", ") || "none"}; variables ${result.variables.map((value) => `${value.name}@L${value.line}`).join(", ") || "none"}. Purposes/parameters: docs/code-map.json.`;
  publish(
    file,
    source
      .split("\n")
      .map((line) => (line.startsWith(marker) ? header : line))
      .join("\n"),
  );
  maps[file] = result;
}
publish("docs/code-map.json", JSON.stringify(maps, null, 2) + "\n");
console.log(
  `Checked ${files.length} source indexes and exact declaration/variable locations.`,
);
