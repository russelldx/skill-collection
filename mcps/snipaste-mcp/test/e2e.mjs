import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { mkdtemp, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const results = [];

function check(name, condition, detail = '') {
  results.push({ name, ok: Boolean(condition), detail });
  console.log(`${condition ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
}

function textOf(result) {
  return (result.content ?? []).filter((block) => block.type === 'text').map((block) => block.text).join('\n');
}

function imageOf(result) {
  return (result.content ?? []).find((block) => block.type === 'image');
}

function pngSize(buffer) {
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

const workDir = await mkdtemp(join(tmpdir(), 'snipaste-mcp-test-'));
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [join(root, 'src', 'server.js')],
  cwd: root,
  env: { ...process.env },
  stderr: 'inherit',
});
const client = new Client({ name: 'snipaste-mcp-e2e', version: '0.0.0' });

try {
  await client.connect(transport);

  const tools = await client.listTools();
  const names = tools.tools.map((tool) => tool.name).sort();
  check('tools/list returns snip_capture, snip_ocr, snip_status', names.join(',') === 'snip_capture,snip_ocr,snip_status', names.join(','));
  check(
    'snip_capture advertises target/area params',
    (tools.tools.find((tool) => tool.name === 'snip_capture')?.inputSchema?.properties?.target) !== undefined,
  );

  let started = Date.now();
  const statusResult = await client.callTool({ name: 'snip_status', arguments: {} });
  const statusInfo = JSON.parse(textOf(statusResult));
  console.log('   status:', JSON.stringify(statusInfo));
  check('snip_status finds the executable', statusInfo.found === true && Boolean(statusInfo.executable), statusInfo.executable);
  const wasRunning = statusInfo.running === true;
  console.log(`   ${wasRunning ? 'Snipaste already running' : 'cold start: Snipaste is stopped'}`);

  started = Date.now();
  const area = await client.callTool({
    name: 'snip_capture',
    arguments: { target: 'area', x: 0, y: 0, width: 320, height: 200 },
  });
  const areaElapsed = Date.now() - started;
  const areaImage = imageOf(area);
  check('snip_capture returns an image block', Boolean(areaImage), `round trip ${areaElapsed} ms`);
  if (areaImage) {
    const size = pngSize(Buffer.from(areaImage.data, 'base64'));
    check('captured image is exactly 320x200', size.width === 320 && size.height === 200, `${size.width}x${size.height}`);
  }
  check('snip_capture reports the saved path', /Saved to: .+\.png/.test(textOf(area)), textOf(area).split('\n')[1]);

  const afterCold = JSON.parse(textOf(await client.callTool({ name: 'snip_status', arguments: {} })));
  check(
    'snip_capture leaves Snipaste running',
    afterCold.running === true,
    wasRunning ? 'already running before the test' : `launched on demand, first capture ${areaElapsed} ms`,
  );
  const reuse = Date.now();
  await client.callTool({ name: 'snip_capture', arguments: { target: 'area', x: 0, y: 0, width: 64, height: 64, include_image: false } });
  console.log(`   second capture after launch: ${Date.now() - reuse} ms`);

  const full = await client.callTool({
    name: 'snip_capture',
    arguments: { target: 'fullscreen', include_image: false },
  });
  const fullText = textOf(full);
  check('fullscreen capture works without returning the image', !imageOf(full) && /Captured \d+x\d+/.test(fullText), fullText.split('\n')[0]);

  const fixedPath = join(workDir, 'fixed.png');
  const firstSave = await client.callTool({
    name: 'snip_capture',
    arguments: { target: 'area', x: 0, y: 0, width: 120, height: 80, save_path: fixedPath, include_image: false },
  });
  const savedFile = await stat(fixedPath).catch(() => null);
  check('save_path writes the file to the given location', Boolean(savedFile) && savedFile.size > 0, `${savedFile?.size ?? 0} bytes`);

  const secondSave = await client.callTool({
    name: 'snip_capture',
    arguments: { target: 'area', x: 0, y: 0, width: 120, height: 80, save_path: fixedPath, include_image: false },
  });
  check('refuses to overwrite unless overwrite=true', secondSave.isError === true, textOf(secondSave).slice(0, 80));

  const overwriteSave = await client.callTool({
    name: 'snip_capture',
    arguments: { target: 'area', x: 0, y: 0, width: 120, height: 80, save_path: fixedPath, overwrite: true, include_image: false },
  });
  check('overwrite=true replaces the file', overwriteSave.isError !== true);

  const invalid = await client.callTool({
    name: 'snip_capture',
    arguments: { target: 'area', x: 0, y: 0, height: 100 },
  });
  check('rejects target=area without width', invalid.isError === true, textOf(invalid).slice(0, 80));

  started = Date.now();
  const ocrResult = await client.callTool({
    name: 'snip_ocr',
    arguments: { target: 'fullscreen', timeout_ms: 6000 },
  });
  const ocrText = textOf(ocrResult);
  const ocrFailedCleanly = ocrResult.isError === true && /PRO feature/i.test(ocrText);
  const ocrSucceeded = ocrResult.isError !== true && ocrText.length > 0;
  check(
    'snip_ocr returns text, or a clear PRO-only error',
    ocrSucceeded || ocrFailedCleanly,
    `${Date.now() - started} ms`,
  );
  console.log('   ocr:', JSON.stringify(ocrText.slice(0, 140)));

  const afterOcr = await client.callTool({
    name: 'snip_capture',
    arguments: { target: 'area', x: 0, y: 0, width: 96, height: 64, include_image: false },
  });
  check(
    'capture still works after a failed OCR',
    afterOcr.isError !== true && /Captured 96x64/.test(textOf(afterOcr)),
    textOf(afterOcr).split('\n')[0],
  );

  void firstSave;
} finally {
  await client.close().catch(() => {});
  await rm(workDir, { recursive: true, force: true }).catch(() => {});
}

const failed = results.filter((result) => !result.ok);
console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
process.exit(failed.length ? 1 : 0);
