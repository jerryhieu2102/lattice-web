import { cp } from "node:fs/promises";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
await cp(
  path.join(root, ".next/static"),
  path.join(root, ".next/standalone/.next/static"),
  { recursive: true },
);
const child = spawn(
  process.execPath,
  [path.join(root, ".next/standalone/server.js")],
  { stdio: "inherit", env: { ...process.env, HOSTNAME: "0.0.0.0" } },
);
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => child.kill(signal));
child.on("exit", (code) => process.exit(code ?? 0));
