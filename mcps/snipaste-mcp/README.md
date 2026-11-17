# snipaste-mcp

这个 MCP 服务通过 [Snipaste](https://www.snipaste.com/) 的命令行截图、读取屏幕文字，不会截到桌面或其他隐私窗口。

## Privacy: captures never include the desktop

`snip_capture` 默认绝不会截取整个桌面。每次截图都只针对一个应用窗口：

1. 通过 `app` / `title` / `pid` 找到窗口（用 `snip_windows` 列出候选窗口），记录窗口状态，并在默认情况下将它最大化，让它填满屏幕。
2. 用 Snipaste 的 `--area` 只截取该窗口的可见矩形区域，绝不截取显示器上的其他区域。
3. 保持窗口不动，对矩形区域内各处的采样点做命中测试：每个点都必须属于目标窗口（窗口自己的弹出窗口和菜单可以通过校验）。只要有其他内容遮挡，就不返回图片。
4. 将窗口恢复到原来的大小和位置。

如果校验失败，会删除 PNG，并返回错误，指出哪个窗口造成了遮挡。`fullscreen`、`active_screen` 和 `last` 都会被拒绝，除非传入 `allow_desktop: true`；这个开关仅限用户明确要求截取桌面时使用。`snip_ocr` 也遵循同样的流程：只有通过相同的校验后，才返回识别出的文字。

没有合适的应用窗口时（需要渲染 HTML、图片、PDF 或 URL），使用 `snip_view`：它会用一次性 profile 打开临时 Edge/Chrome 窗口来显示内容，截取该窗口后再关闭浏览器。整个过程绝不会操作用户自己的浏览器窗口、标签页或登录态。

## Tools

| Tool | What it does |
|---|---|
| `snip_capture` | 默认截取一个窗口，也可截取窗口内的矩形区域；使用 `allow_desktop` 时可截取桌面。将 PNG 作为 MCP 图片块返回，同时返回保存路径和图片尺寸。 |
| `snip_view` | 在专用的临时浏览器窗口中渲染文件、URL 或 HTML 页面，然后截取该窗口。 |
| `snip_windows` | 以只读方式列出可见的顶层窗口，供选择截图目标。列出的信息包括应用（app）、标题（title）、进程 id（pid）、矩形区域（rectangle）、是否最大化（maximized）和是否在前台（foreground）。 |
| `snip_ocr` | 用 Snipaste 从一个通过校验的窗口中提取文字。**仅限 PRO**，详见下文。 |
| `snip_status` | 显示找到 Snipaste 的位置、版本、运行状态、是否支持窗口控制、检测到的浏览器，以及前台窗口。 |

### `snip_capture` parameters

| Parameter | Type / default | Meaning |
|---|---|---|
| `target` | `'window' \| 'area' \| 'fullscreen' \| 'active_screen' \| 'last'`，默认 `'window'` | `window`：一个通过校验的窗口。`area`：窗口内的矩形区域。后三种会截取桌面，除非传入 `allow_desktop: true`，否则拒绝使用。 |
| `app` | string?，进程名，不含 `.exe` | 按进程选择窗口。 |
| `title` | string?，正则表达式 | 进程有多个窗口时，用它选出一个。 |
| `pid` | number? | 按进程 id 选择窗口；有多个实例时，这种方式最可靠。 |
| `mode` | `'maximize' \| 'keep'`，默认 `'maximize'` | `maximize` 在截图前让窗口填满屏幕；`keep` 保持窗口原位，只要有任何内容遮挡就拒绝截图。`area` 始终按 keep 模式处理。 |
| `settle_ms` | number，默认 500 | 移动窗口后、检查遮挡前的等待时间，让应用有时间重绘。 |
| `restore` | boolean，默认 true | 截图后将窗口放回原位，并取消最大化。 |
| `allow_desktop` | boolean，默认 false | 显式允许使用 `fullscreen` / `active_screen` / `last`。 |
| `x` `y` `width` `height` | numbers，适用于 `area` | 以屏幕像素为单位的矩形区域，必须完全位于窗口的可见矩形区域内。 |
| `delay` | number，默认 0 | 截图前等待的秒数。 |
| `shadow` | boolean，默认 false | 仅限 PRO，免费版会忽略此参数，window/area 截图也会忽略它。 |
| `save_path` | string? | PNG 的绝对路径。默认使用操作系统临时目录下的唯一文件。目录不存在时会创建，也支持非 ASCII 名称。 |
| `overwrite` | boolean，默认 true | 设为 `false` 时，如果文件已存在，调用会失败，不会覆盖文件。 |
| `include_image` | boolean，默认 true | 设为 `false` 时，只返回路径和图片尺寸。 |
| `timeout_ms` | number，默认 8000 | 等待 Snipaste 写完文件的时长。 |

### `snip_view` parameters

| Parameter | Type / default | Meaning |
|---|---|---|
| `file` / `url` / `html` | 必须且只能选一个 | 本地文件、http(s)/file URL 或 HTML 源码（先写入临时文件）。 |
| `browser` | `'auto' \| 'edge' \| 'chrome'`，默认 `auto` | `auto` 按 Edge、Chrome 的顺序选择第一个已安装的浏览器；显式指定浏览器后，绝不会回退到其他浏览器。 |
| `width` / `height` | numbers | 窗口大小，默认为主显示器的工作区大小。 |
| `kiosk` | boolean，默认 false | 设为 `true` 时，使用浏览器的 kiosk 模式，而不是应用样式窗口。 |
| `wait_ms` | number，默认 1200 | 窗口出现后的等待时间，让页面有时间渲染。 |
| `save_path` / `overwrite` / `include_image` / `timeout_ms` | 同上 | 含义与 `snip_capture` 中相同。 |

### `snip_windows` parameters

`app`、`title`、`pid` 都是可选的筛选条件；`limit` 默认 20，最大 100。此工具只读。

### Choosing a tool

- 内容在用户能指明的应用窗口中 → 使用 `snip_capture`，并设为 `target: 'window'`（默认流程）。
- 内容是文件、URL 或 HTML，或者应用窗口无法截出干净的画面 → 使用 `snip_view`。
- 不确定选哪个窗口 → 先用 `snip_windows`，再按 `app` / `title` / `pid` 截图。
- 截取桌面 → 仅限用户明确提出要求，并传入 `allow_desktop: true` 时。

## How a window capture stays private

- **Rectangle**：取 DWM 扩展边框（用户实际看到的像素，不含 Windows 不可见的缩放边框）与显示器工作区的交集。`keep` 模式还会在每边向内缩进 8 px，避免截到圆角处透出的后方窗口像素。
- **Coverage check**：在矩形区域内布置网格，对最多 ~400 个采样点做命中测试；每个点对应的根窗口都必须是目标窗口（同一进程的窗口可以通过校验）。处于 Cloaked 状态的窗口和完全透明的窗口不绘制任何内容，因此会跳过。
- **Transient overlays**：如果通知提示在截图后、校验前滑入并遮住窗口的一条边，只要剩下的干净矩形区域至少为 320x200，且不小于原区域的 60%，就裁去被遮挡的边缘，再对剩余区域重新截图并校验。否则拒绝本次调用。调用方收到的像素一定都通过了截图后的校验。
- **Restore**：用 `SetWindowPos` 恢复窗口原来的大小、位置和最大化状态；如果窗口被应用隐藏，还会重新显示它。

## Requirements

- Snipaste 2.x，便携版也可以；不要求加入 `PATH`。
- Node.js 18+.
- 当前版本中，**窗口截图和 `snip_view` 仅支持 Windows**。在其他平台上，`snip_capture` 会拒绝调用，除非先征得用户同意，再传入 `allow_desktop: true`；其他窗口工具会报错 "Windows-only"。
- `snip_view` 需要 Microsoft Edge（Windows 自带）或 Google Chrome。
- 在 Windows 上，通过 PowerShell 读取剪贴板（OCR 需要）。

## Setup

```bash
npm install
npm test          # end-to-end test against the local Snipaste install
```

`npm test` 会调用本机真实的 Snipaste：打开专用的 WinForms 测试窗口（绝不会使用 Notepad 或用户的任何文档），截取经过校验的小图，写入临时目录后再删除。在免费版中，OCR 用例预期会失败，并报错提示需要 PRO。

将它注册到 MCP 客户端：

```json
{
  "mcpServers": {
    "snipaste": {
      "command": "node",
      "args": ["<path-to>/snipaste-mcp/src/server.js"]
    }
  }
}
```

按以下顺序查找可执行文件：已设置的 `SNIPASTE_PATH`、常见安装目录
（`Program Files`、`%LOCALAPPDATA%\Programs`、`/Applications`）、`PATH`、上次运行时缓存的路径、
正在运行的进程路径，最后在 `Desktop`、`Downloads`、`Documents` 和
`%LOCALAPPDATA%\Programs` 中做有限范围的扫描。首次找到的路径会缓存到用户配置目录，所以即使便携版
没有运行、也不在 `PATH` 中，只需查找一次，之后就能立即定位。

如果 Snipaste 没有运行，会以分离进程的方式启动，首次截图会等待它启动：这次调用预计约 2.5 s，
后续为 ~0.3 s。

## Free vs PRO

这里能用哪些功能，以 Snipaste 自己的对照表为准。免费版的情况如下：

- 可用：区域 / 全屏 / 活动屏幕截图、重复上次截图、`--delay`、保存到文件、复制到剪贴板。
- 会被忽略，且不报错：`--active-window`、`--shadow`、`-o ocr_clipboard`、`--block`，以及组合多个 `-o` 输出。

因为 `--active-window` 会被忽略，这个服务自行控制窗口：通过 Win32 读取窗口的矩形区域，
再用 `--area` 精确截取该区域。无法解析的 `--area` 参数同样会被忽略，且不报错，
所以服务会仔细计算坐标，并在截图前后进行校验。

Snipaste 的两种行为影响了这个设计：

- 免费版的 `-o ocr_clipboard` 不只是没有输出：应用仍在运行，却不再响应
  后续的 `snip` 命令，导致 OCR 失败后的每次截图都超时。`snip_ocr` 检测到超时后，会重启
  Snipaste 来恢复截图功能，再返回错误，明确提示需要 PRO。
- 服务从不使用 `--block`。在 Snipaste 2.9.2 中，它会完全阻止文件输出；服务通过轮询
  判断输出文件是否停止增长，或剪贴板是否变化，以此判断操作是否完成。

## Limitations

- 每次窗口截图都要额外与 PowerShell 往返两次来控制窗口：冷启动约 +1.5 s，热启动 ~+1 s。
- 前台锁可能让已最大化的窗口无法真正置前；此时遮挡校验会失败，
  调用也会被拒绝。点击一次目标窗口后重试；服务绝不会降级为桌面截图。
- 如果置顶小组件（迷你音乐播放器、通知横幅）遮住窗口边缘，只要剩下的干净矩形区域足够大，
  就裁去被遮挡的部分，否则拒绝截图。这是有意的设计。
- 多显示器：只截取目标窗口本身的矩形区域，绝不会包含其他显示器。
- 如果 Node 进程在截图中途被终止，窗口会保持最大化，因为已没有机会恢复它。
- `keep` 模式会在矩形区域的每边向内缩进 8 px，不会截取圆角窗口最外侧的一圈。

## Notes

- 截图默认保存为操作系统临时目录下的唯一文件（`snipaste-mcp/`）。传入 `save_path` 可保存到其他位置。
- `snip_ocr` 会覆盖系统剪贴板；如果没有识别到文字，Snipaste 会清空剪贴板。
- 截图超时也可能是因为 Snipaste 选区窗口开着，正在等待点击；关闭它后重试。
- 坐标使用物理屏幕像素（支持按显示器感知 DPI），与 Snipaste 的 `--area` 使用相同单位。
