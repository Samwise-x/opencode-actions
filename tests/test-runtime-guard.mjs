#!/usr/bin/env node
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"

const source = await readFile(new URL("../templates/harden-runtime.js", import.meta.url), "utf8")
const moduleUrl = "data:text/javascript;base64," + Buffer.from(source).toString("base64")
const { HardenRuntime } = await import(moduleUrl)
const hooks = await HardenRuntime()

process.env.OPENCODE_TEST_SECRET = "should-not-cross"
const output = { env: { OPENCODE_TEST_SECRET: "should-not-cross" } }
await hooks["shell.env"]({}, output)
assert.equal(output.env.OPENCODE_TEST_SECRET, "")

for (const command of [
  "gh issue list",
  "git push origin HEAD",
  "/usr/bin/git commit -m nope",
  "sudo true",
  "nohup sleep 10",
]) {
  await assert.rejects(
    () => hooks["tool.execute.before"]({ tool: "bash" }, { args: { command } }),
    /command rejected/,
  )
}

await hooks["tool.execute.before"](
  { tool: "bash" },
  { args: { command: "git status --porcelain" } },
)

console.log("runtime guard tests passed")
