# Template authoring & placeholder reference

How `docx-pro` uses templates, and how to add your own.

## Two ways to use a template

### 1. Reference-document styling (recommended for prose)

Pass a `.docx` as `--reference` to `md_to_docx.py`. pandoc copies that file's
styles (fonts, heading styles, margins, header/footer) and pours your Markdown
content into them. The reference doc's *body text is ignored* — only its styles
and section setup are used.

Use an optional user-supplied template; set `TEMPLATE` to its actual absolute
path. No business DOCX templates are bundled with this skill.

```bash
python -c 'import pathlib,sys; sys.exit(0 if pathlib.Path(sys.argv[1]).is_file() else "Template not found")' "$TEMPLATE" && \
  python scripts/md_to_docx.py body.md out.docx --reference "$TEMPLATE"
```

Without a template, run `python scripts/md_to_docx.py body.md out.docx`
(no `--reference`), or use the Node renderer/docx-js route in SKILL.md.

Best for: reports, memos, letters where the structure comes from your Markdown
and you just want consistent house styling.

### 2. Placeholder replacement (recommended for fixed forms)

For documents with a fixed layout and a few variable fields (contracts, cover
pages), put literal `{{token}}` placeholders in the template and fill them:

```bash
python -c 'import pathlib,sys; sys.exit(0 if pathlib.Path(sys.argv[1]).is_file() else "Template not found")' "$TEMPLATE" && \
  python scripts/fill_template.py "$TEMPLATE" out.docx \
    --set title="服务采购合同" --set party_a="甲方公司" \
    --set party_b="乙方公司" --set date="2026-06-17"
```

`fill_template.py` merges runs within each paragraph before replacing, so it
works even when Word has split a token like `{{title}}` across multiple runs
(a common reason naive replacement fails). Use distinct, fully resolved
template and output paths and an approved non-overwriting output: the script
writes to the output path you give it, so that precondition is what keeps the
template file itself untouched — it does not enforce a no-overwrite guarantee
on its own.

## Placeholder conventions

- Use `{{snake_case}}` tokens: `{{title}}`, `{{party_a}}`, `{{effective_date}}`.
- One token = one logical field. Don't embed formatting inside a token.
- Keep tokens on their own run/line where possible for cleanest replacement.
- After filling, the script reports any **unfilled** tokens still present —
  treat that as a checklist, not a silent pass.

## Template availability

Reports, memos, letters, contracts and minutes are possible document types,
not shipped template files. Inspect a user-supplied template's actual styles
and tokens before use. If the path is missing, stop template filling and offer
the no-template route; do not silently substitute a fictitious bundled file.

## Creating a new template

1. If the user requests a reusable template, build the document with the base
   `docx` skill (full control over styles, header/footer, tables).
2. Where a field should be variable, insert a literal `{{token}}` as plain
   text in its own run.
3. Save the `.docx` in the user's chosen output directory, not the installed skill.
4. Explain its tokens in the delivery message.
5. Verify the saved path exists, then use `fill_template.py` (tokens) or
   `--reference` (styling).

## CJK templates

For Chinese templates, build them with the base skill using the preset in
`scripts/styles/zh-cn.js` so heading/body fonts declare `eastAsia`. This keeps
rendering consistent across macOS / Windows / WPS.
