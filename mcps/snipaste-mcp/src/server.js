#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { capture, ocr, status } from './snipaste.js';

const server = new McpServer({ name: 'snipaste', version: '0.1.0' });

const target = z
  .enum(['fullscreen', 'active_screen', 'active_window', 'last', 'area'])
  .default('fullscreen')
  .describe(
    "What to capture: 'fullscreen' = entire desktop, 'active_screen' = the screen under the cursor, " +
      "'active_window' = the foreground window (PRO only, ignored on the free build), 'last' = reuse the " +
      "previous snipping area, 'area' = the explicit rectangle given by x/y/width/height.",
  );

const areaFields = {
  x: z.number().int().describe('Left edge in screen pixels (negative allowed on multi-monitor setups). Required when target is "area".').optional(),
  y: z.number().int().describe('Top edge in screen pixels. Required when target is "area".').optional(),
  width: z.number().int().positive().describe('Capture width in pixels. Required when target is "area".').optional(),
  height: z.number().int().positive().describe('Capture height in pixels. Required when target is "area".').optional(),
};

// Kept as plain z.object schemas: the SDK's JSON Schema conversion skips ZodEffects,
// so a superRefine wrapper would advertise an empty parameter list to clients.
const inputSchema = z.object({
  target,
  ...areaFields,
  delay: z.number().min(0).max(30).default(0).describe('Seconds to wait before capturing, for transient UI.'),
  shadow: z.boolean().default(false).describe('Add a drop shadow. PRO only; ignored on the free build.'),
  save_path: z.string().optional().describe('Absolute path to write the PNG to. Defaults to a unique file in the OS temp directory.'),
  overwrite: z.boolean().default(false).describe('Allow replacing an existing file at save_path.'),
  include_image: z.boolean().default(true).describe('Return the screenshot itself in the response. Set false to get only the file path and dimensions.'),
  timeout_ms: z.number().int().min(500).max(30000).default(8000).describe('How long to wait for Snipaste to finish writing the file.'),
});

const ocrInputSchema = z.object({
  target,
  ...areaFields,
  delay: z.number().min(0).max(30).default(0).describe('Seconds to wait before capturing.'),
  timeout_ms: z.number().int().min(500).max(60000).default(6000).describe('How long to wait for OCR text to land in the clipboard.'),
});

function missingAreaFields(geometry) {
  if (geometry.target !== 'area') return [];
  return ['x', 'y', 'width', 'height'].filter((key) => geometry[key] === undefined);
}

const areaOf = ({ target: kind, x, y, width, height }) =>
  kind === 'area' ? { x, y, width, height } : undefined;

const asError = (error) => ({
  isError: true,
  content: [{ type: 'text', text: error instanceof Error ? error.message : String(error) }],
});

server.registerTool(
  'snip_capture',
  {
    title: 'Screenshot with Snipaste',
    description:
      'Capture the screen through Snipaste and return the PNG. Supports the whole desktop, the screen under the ' +
      'cursor, the foreground window, an explicit rectangle, or the previous selection. Snipaste is launched ' +
      'automatically if it is not running. Prefer this over shell-based screen capture on Windows: it is faster, ' +
      'and the result is returned as an image you can inspect.',
    inputSchema,
    annotations: { readOnlyHint: false, openWorldHint: false },
  },
  async ({ target: kind, x, y, width, height, delay, shadow, save_path, overwrite, include_image, timeout_ms }) => {
    const missing = missingAreaFields({ target: kind, x, y, width, height });
    if (missing.length) return asError(new Error(`target "area" requires: ${missing.join(', ')}`));
    try {
      const shot = await capture({
        target: kind,
        area: areaOf({ target: kind, x, y, width, height }),
        delay,
        shadow,
        savePath: save_path,
        overwrite,
        timeoutMs: timeout_ms,
      });
      const content = [
        {
          type: 'text',
          text:
            `Captured ${shot.width}x${shot.height} (${Math.round(shot.bytes / 1024)} KB) from ${kind} ` +
            `in ${shot.elapsedMs} ms.\nSaved to: ${shot.path}`,
        },
      ];
      if (include_image) {
        content.push({ type: 'image', data: shot.buffer.toString('base64'), mimeType: 'image/png' });
      }
      return { content };
    } catch (error) {
      return asError(error);
    }
  },
);

server.registerTool(
  'snip_ocr',
  {
    title: 'OCR text off the screen with Snipaste',
    description:
      'Capture a region with Snipaste and return the text Snipaste recognizes in it. This uses Snipaste\'s built-in ' +
      'text extraction, which is a PRO feature: on the free build the output is silently ignored and Snipaste stops ' +
      'answering later captures, so this call fails with a clear error after restarting Snipaste. It overwrites the ' +
      'system clipboard, which is cleared when recognition finds nothing.',
    inputSchema: ocrInputSchema,
    annotations: { readOnlyHint: false, openWorldHint: false },
  },
  async ({ target: kind, x, y, width, height, delay, timeout_ms }) => {
    const missing = missingAreaFields({ target: kind, x, y, width, height });
    if (missing.length) return asError(new Error(`target "area" requires: ${missing.join(', ')}`));
    try {
      const result = await ocr({
        target: kind,
        area: areaOf({ target: kind, x, y, width, height }),
        delay,
        timeoutMs: timeout_ms,
      });
      if (!result.changed) {
        return asError(
          new Error(
            `Snipaste wrote nothing to the clipboard within ${timeout_ms} ms. Text extraction ("-o ocr_clipboard") ` +
              'is a Snipaste PRO feature; the free build ignores it silently and also stops answering later ' +
              'capture requests. ' +
              (result.recovered ? 'Snipaste has been restarted so captures work again. ' : '') +
              'Use an external OCR tool on a screenshot from snip_capture instead.' +
              (result.text ? `\nClipboard still contains: ${result.text.slice(0, 200)}` : ''),
          ),
        );
      }
      const text = result.text.trim();
      return {
        content: [
          {
            type: 'text',
            text: text || '(no text recognized - Snipaste clears the clipboard when OCR finds nothing)',
          },
        ],
      };
    } catch (error) {
      return asError(error);
    }
  },
);

server.registerTool(
  'snip_status',
  {
    title: 'Snipaste status',
    description:
      'Report whether the Snipaste executable was found, its path and version, and whether it is currently running. ' +
      'Call this first when a capture fails, or to verify SNIPASTE_PATH configuration.',
    annotations: { readOnlyHint: true, openWorldHint: false },
  },
  async () => {
    try {
      const info = await status();
      return { content: [{ type: 'text', text: JSON.stringify(info, null, 2) }] };
    } catch (error) {
      return asError(error);
    }
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
process.stderr.write('snipaste-mcp ready\n');
