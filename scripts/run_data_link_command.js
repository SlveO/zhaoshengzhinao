const { spawnSync } = require("node:child_process");
const path = require("node:path");

const command = process.argv[2];
const root = path.resolve(__dirname, "..");
const isWindows = process.platform === "win32";
const python = isWindows ? "py" : "python3";
const utf8Flag = isWindows ? ["-X", "utf8"] : [];

const targets = {
  demo: ["scripts/data_link_demo.py"],
  interactive: ["scripts/data_link_interactive.py"],
  test: ["tests/test_data_link.py"],
};

if (!targets[command]) {
  console.error("Usage: node scripts/run_data_link_command.js <demo|interactive|test>");
  process.exit(1);
}

const env = { ...process.env };
env.PYTHONPATH = env.PYTHONPATH
  ? `backend${path.delimiter}${env.PYTHONPATH}`
  : "backend";

const result = spawnSync(
  python,
  [...utf8Flag, targets[command][0]],
  { cwd: root, env, stdio: "inherit" },
);

process.exit(result.status ?? 1);
