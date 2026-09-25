import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { createReadStream, createWriteStream, existsSync } from "node:fs";
import { mkdir, rename, writeFile } from "node:fs/promises";
import { pipeline } from "node:stream/promises";
import { createBrotliDecompress } from "node:zlib";
import path from "node:path";
import { extract } from "tar-fs";
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const env = { ...process.env };
if (
  process.platform === "linux" &&
  process.arch === "x64" &&
  !env.CHROMIUM_EXECUTABLE_PATH
) {
  const { default: chromium } = await import("@sparticuz/chromium");
  const source = path.join(root, "node_modules/@sparticuz/chromium/bin");
  const destination = path.join(root, ".browser");
  await mkdir(destination, { recursive: true });
  if (!existsSync(path.join(destination, "ready"))) {
    // Retain the current user's ownership. No privileged chown is needed in containers.
    await pipeline(
      createReadStream(path.join(source, "chromium.br")),
      createBrotliDecompress(),
      createWriteStream(path.join(destination, "chromium.part"), {
        mode: 0o700,
      }),
    );
    await rename(
      path.join(destination, "chromium.part"),
      path.join(destination, "chromium"),
    );
    for (const [archive, folder] of [
      ["fonts.tar.br", "fonts"],
      ["swiftshader.tar.br", "."],
    ]) {
      await pipeline(
        createReadStream(path.join(source, archive)),
        createBrotliDecompress(),
        extract(path.join(destination, folder), { chown: false }),
      );
    }
    await writeFile(path.join(destination, "ready"), "ok");
  }
  await writeFile(
    path.join(destination, "fonts", "fonts.conf"),
    `<?xml version="1.0"?><fontconfig><dir>${path.join(destination, "fonts", "fonts")}</dir><dir>/usr/share/fonts</dir><cachedir>${path.join(destination, "font-cache")}</cachedir></fontconfig>`,
  );
  env.FONTCONFIG_PATH = path.join(destination, "fonts");
  env.LD_LIBRARY_PATH =
    destination + (env.LD_LIBRARY_PATH ? ":" + env.LD_LIBRARY_PATH : "");
  env.CHROMIUM_EXECUTABLE_PATH = path.join(destination, "chromium");
  env.CHROMIUM_ARGS = JSON.stringify(
    chromium.args.filter(
      (x) =>
        ![
          "--disable-web-security",
          "--allow-running-insecure-content",
          "--single-process",
        ].includes(x),
    ),
  );
}
const result = spawnSync(
  process.execPath,
  [
    path.join(root, "node_modules/@playwright/test/cli.js"),
    "test",
    ...process.argv.slice(2),
  ],
  { cwd: root, env, stdio: "inherit" },
);
process.exit(result.status ?? 1);
