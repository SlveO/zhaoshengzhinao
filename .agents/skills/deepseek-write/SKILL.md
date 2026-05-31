---
name: deepseek-write
description: Use when Opus/Haiku (DeepSeek-backed) needs to write or edit files. Uses Bash heredoc as primary method, with sed/python3 for edits. Invoke before ANY file write operation.
---

# DeepSeek-Safe File Operations

DeepSeek-backed models (Opus, Haiku) produce "Invalid tool parameters" on ~30% of Write/Edit tool calls — the model cannot reliably JSON-encode file content containing special characters (backticks, quotes, backslashes, template literals, etc.).

## Iron Rule

**Write tool: NEVER. Edit tool: NEVER. Bash heredoc: ALWAYS.**

This applies to ALL file creation and modification, no exceptions.

---

## 1. Create a New File

Use `cat > path << 'HEREDOC_DELIMITER'` with a **quoted** delimiter (single quotes around ENDOFFILE prevent shell variable expansion):

```bash
cat > /absolute/path/to/file.ts << 'ENDOFFILE'
// content exactly as written — no escaping needed
const greeting = `Hello ${name}`;
const regex = /[\w]+/g;
const obj = { "key": "value with \"embedded\" quotes" };
ENDOFFILE
```

### Choosing a delimiter

- Default: `ENDOFFILE`
- If the file content contains the string `ENDOFFILE`, pick a different delimiter: `EOFMARKER`, `HEREDOC_END`, `FILEEND`, etc.
- The delimiter **must not appear** anywhere in the file content
- Always quote the delimiter with single quotes to prevent shell expansion of `$`, backticks, and `\` inside the heredoc

### Multi-line content works naturally

```bash
cat > /path/to/component.tsx << 'ENDOFFILE'
import React from 'react';

export default function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border p-4">
      <h3 className="text-lg font-bold">{title}</h3>
      {children}
    </div>
  );
}
ENDOFFILE
```

No escaping, no quoting gymnastics — the heredoc preserves everything literally.

---

## 2. Edit an Existing File

### Method A: sed replacement (preferred for small, targeted edits)

Replace an exact string with a new string:

```bash
sed -i 's|old_string|new_string|g' /absolute/path/to/file.py
```

**Delimiter choice**: Use `|` as the sed delimiter when content contains `/` (common in file paths and HTML). If content contains `|`, use `#` or `@` instead.

```bash
# Path-containing example
sed -i 's|from "old/path/module"|from "new/path/module"|g' /path/to/file.ts

# HTML-containing example
sed -i 's|<div class="old">|<div class="new">|g' /path/to/component.tsx
```

**Multi-line replacement** with sed is fragile — prefer python3 for those cases.

### Method B: python3 string replace (for multi-line edits or content with special characters)

```bash
python3 -c "
import pathlib
p = pathlib.Path('/absolute/path/to/file.py')
content = p.read_text(encoding='utf-8')
content = content.replace(
    'old text that spans\nmultiple lines',
    'new text that spans\nmultiple lines'
)
p.write_text(content, encoding='utf-8')
"
```

For replacements involving complex strings (regex special chars, lots of quotes), use a **separate variable** to avoid shell escaping hell:

```bash
python3 << 'PYEOF'
import pathlib

p = pathlib.Path('/absolute/path/to/file.py')
content = p.read_text(encoding='utf-8')

old = '''old text
with "all sorts" of 'quotes' and $ymbols
and back\slashes'''

new = '''replacement text
also multi-line'''

content = content.replace(old, new)
p.write_text(content, encoding='utf-8')
PYEOF
```

### Method C: Line-range replacement (delete + insert)

When you need to replace a block of lines by line number:

```bash
# Replace lines 10-20 with new content
python3 << 'PYEOF'
import pathlib

p = pathlib.Path('/absolute/path/to/file.py')
lines = p.read_text(encoding='utf-8').splitlines(keepends=True)

new_lines = [
    "def new_function():\n",
    "    return 'hello'\n",
]

# Replace lines 10-20 (0-indexed: 9-19) with new_lines
result = lines[:9] + new_lines + lines[20:]
p.write_text(''.join(result), encoding='utf-8')
PYEOF
```

---

## 3. JSON Files (Extra Caution)

For JSON files, use `jq` to ensure valid output:

```bash
# Write a JSON file safely
cat > /path/to/config.json << 'ENDOFFILE'
{
  "name": "my-app",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite --port 3001",
    "build": "vite build"
  }
}
ENDOFFILE

# Verify it's valid JSON
jq empty /path/to/config.json && echo "Valid JSON" || echo "INVALID JSON"
```

For programmatic JSON edits, always use `jq`:

```bash
# Add a field to package.json
jq '.scripts.test = "vitest run"' /path/to/package.json > /tmp/tmp.json && mv /tmp/tmp.json /path/to/package.json
```

---

## 4. Binary / Non-Text Files

For non-text files (images, fonts, compiled assets), use `base64`:

```bash
# Decode a base64-encoded binary file
echo 'iVBORw0KGgoAAAANS...' | base64 -d > /path/to/image.png
```

---

## 5. Verification

After every write/edit, verify the file was written correctly:

```bash
# Quick check: file exists and has content
wc -l /absolute/path/to/file && echo "File written successfully"

# Content spot-check: verify a key string appears
grep -c "expected_string" /absolute/path/to/file
```

For critical files, read back the file and confirm the content matches what you intended.

---

## 6. Fallback Chain

If the Bash heredoc approach fails:

1. **Retry** the heredoc — check for delimiter conflicts or shell quoting issues
2. **Tool-writer sub-agent** — spawn a Sonnet sub-agent (which does NOT have the DeepSeek Write bug):
   ```
   Agent({subagent_type:"tool-writer", model:"sonnet", prompt:"Write file /path/to/file with content: ..."})
   ```
3. **Record block** — if all retries fail, append to `reports/block.md`:
   ```
   - [timestamp] BLOCKED: Write/Edit on /path/to/file — Reason: [error message]
   ```

---

## 7. Quick Reference

| Task | Command |
|------|---------|
| Create file | `cat > path << 'ENDOFFILE'` |
| Edit single line | `sed -i 's\|old\|new\|g' path` |
| Edit multi-line | `python3 << 'PYEOF' ... PYEOF` |
| Edit JSON | `jq '.key = "val"' file > /tmp/t.json && mv /tmp/t.json file` |
| Verify write | `wc -l path && echo "OK"` |
| Fallback | `Agent({subagent_type:"tool-writer", model:"sonnet"})` |
