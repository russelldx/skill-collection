---
name: web-artifacts-builder
description: Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn/ui). Use for complex artifacts requiring state management, routing, or shadcn/ui components - not for simple single-file HTML/JSX artifacts.
license: Complete terms in LICENSE.txt
---

# Web Artifacts Builder

To build frontend claude.ai artifacts, follow these steps:
1. Resolve the installed skill's directory to an absolute path and keep it in `SKILL_DIR` for the whole session — generated projects do not contain the skill's `scripts/`, so helpers must be invoked through that absolute path. Inspect `scripts/init-artifact.sh` and obtain authorization for its dependency installation and target directory before initializing a new project. Do not overwrite an existing project.
2. Develop your artifact by editing the generated code.
3. Inspect and run `scripts/bundle-artifact.sh` (through `SKILL_DIR`) after authorization for its dependency and configuration changes.
4. Test the development app and bundled HTML in a browser, including key interactions, an edge case, and console errors.
5. Share the artifact and report the observed verification results or explicit testing limitations.

**Stack**: React 18 + TypeScript + Vite + Parcel (bundling) + Tailwind CSS + shadcn/ui

## Design & Style Guidelines

VERY IMPORTANT: To avoid what is often referred to as "AI slop", avoid using excessive centered layouts, purple gradients, uniform rounded corners, and Inter font.

## Quick Start

### Step 1: Initialize Project

Resolve the skill directory once (absolute path of the folder containing this `SKILL.md`), then run the initialization script from there to create a new React project:

```bash
SKILL_DIR="<absolute path to this skill directory>"
bash "$SKILL_DIR/scripts/init-artifact.sh" <project-name>
cd <project-name>
```

This creates a fully configured project with:
- ✅ React + TypeScript (via Vite)
- ✅ Tailwind CSS 3.4.1 with shadcn/ui theming system
- ✅ Path aliases (`@/`) configured
- ✅ 40+ shadcn/ui components pre-installed
- ✅ All Radix UI dependencies included
- ✅ Parcel configured for bundling (via .parcelrc)
- ✅ Node 18+ support is the script's intent — it enforces Node ≥ 18 and pins Vite 5.4.11 on Node 18 (latest on Node 20+); verify against the Node version actually installed

### Step 2: Develop Your Artifact

To build the artifact, edit the generated files.

### Step 3: Bundle to Single HTML File

To bundle the React app into a single HTML artifact, run from the project root (the generated project does not contain the skill's scripts):

```bash
bash "$SKILL_DIR/scripts/bundle-artifact.sh"
```

This creates `bundle.html` with the built JavaScript, CSS, and bundled dependencies inlined via html-inline. Verify the output before claiming it is self-contained — assets fetched at runtime from external URLs (CDN fonts, remote images, APIs) are not inlined. This file can be directly shared in Claude conversations as an artifact.

**Requirements**: Your project must have an `index.html` in the root directory.

**What the script does**:
- Installs bundling dependencies (parcel, @parcel/config-default, parcel-resolver-tspaths, html-inline)
- Creates `.parcelrc` config with path alias support
- Builds with Parcel (no source maps)
- Inlines the built dist assets into a single HTML file using html-inline (verify the output; runtime external URLs are not inlined)

### Step 4: Test Before Claiming Completion

Start the development server and exercise the feature with an available browser tool. Also open the bundled output and verify its core interactions and console. A successful build alone does not establish feature correctness. If browser testing is unavailable or not authorized, disclose that limitation and label the artifact unverified rather than claiming completion.

### Step 5: Share Artifact with User

Share the bundled HTML file with the user, including a concise account of what was actually tested. Sharing a local result does not authorize publishing it to an external service.

## Reference

- **shadcn/ui components**: https://ui.shadcn.com/docs/components