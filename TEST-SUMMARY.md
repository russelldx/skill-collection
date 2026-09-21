# 验证范围与复现方法

本仓库不再使用“63 个 skill 全部可用”或“所有 agent 完全兼容”的结论。全文审查、结构检查、隔离脚本测试和真实平台验收是不同层次；一层通过不能代替另一层。

## 结构验证

```bash
python validate-skills.py
bash validate-skills.sh
```

两条命令调用同一验证器，失败返回非零退出码。检查范围：

- `skills/` 下 55 个活动入口，必需 frontmatter 字段和名称唯一性。
- 不允许参考目录中嵌套 `SKILL.md`；归档入口改为 `REFERENCE.md`。
- `INDEX.md` 对活动技能的完整、无重复覆盖。
- 活动 `SKILL.md` 及根目录说明中的实际本地 Markdown 链接（不验证网页、锚点或代码示例）。
- 本地链接大小写，即使在 Windows 上也能发现 Linux 下失效的引用。
- MCP JSON 可解析，Chrome DevTools 包名正确，没有无效 claude-mem 包声明。

验证器只检查必需 frontmatter 字段，不是完整 YAML 解析器；也不执行技能自然语言指令或验证全部正文承诺。

## 隔离回归

在仓库根目录执行（Git Bash / POSIX shell）：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_repository_validation.py' -v
node --test skills/web-access/scripts/audit-safety.test.mjs
PYTHONUTF8=1 python -B skills/anthropic-xlsx/scripts/test_recalc.py
PYTHONUTF8=1 python -B skills/course-assignment/scripts/test_verify_media.py
PYTHONUTF8=1 python -B skills/course-assignment/scripts/test_gen_docx.py
PYTHONUTF8=1 python -B skills/xls-poi/scripts/test_paused.py
```

| 测试 | 本轮结果 | 实际覆盖 |
|------|----------|----------|
| 仓库验证器 | 17 项通过 | frontmatter 必填字段、链接大小写/相对路径、代码示例排除、索引、归档、MCP 包操作数及缺失命令 |
| web-access | 9 项通过 | 注入假的浏览器发现结果，验证严格选择、Proxy 复用和授权诊断；不启动浏览器或监听端口 |
| LibreOffice 重算 | 8 项通过 | 模拟外部进程，验证临时 profile、完成标记、失败/超时清理和 Windows 拒绝执行；未真实重算 |
| DOCX 图片校验 | 4 项通过 | 比较媒体内容字节、发现缺图、错误输入及非零退出码 |
| 课程 DOCX 生成 | 3 项通过，无跳过 | 缺依赖预检查，以及使用现有 docx 包真实生成包含表格和图片的 DOCX，再校验媒体 |
| POI 删列停用 | 4 项通过 | 真实编译运行拒绝入口，确认输入/输出不变；其他命令只验证参数转发，不代表 POI 工作簿功能已验收 |

测试在临时目录中生成样本并清理，不使用真实用户文件。运行前需要现有 Python/openpyxl、Node.js、Java 和 Bash；DOCX 生成测试在缺少现有 docx 包时会明确跳过，不能把跳过记作通过。验证器测试数量不代表全部技能的功能覆盖。

此外，按原路径到合并/归档路径的映射核对了 64 个原有受版本控制文件，未发现资源缺失；两份旧 POI 删列 Java 源码保存在非执行参考目录，规范化换行后与原版一致。

## 真实环境中仍需验证

| 路线 | 必须另行验证的内容 |
|------|------------------|
| 文档生成 | 本机依赖、实际文件打开、渲染质量、公式结果、格式和数据验证保留 |
| LibreOffice 重算 | 外部程序可用，临时 profile 隔离，以及重算输出的实际正确性 |
| POI 删列 | 暂停；旧验证器的 `MISMATCHES=0` 不覆盖全部保真条件 |
| Chrome DevTools / web-access | 调试授权、浏览器/profile 归属、实际页面读取与交互 |
| Firecrawl | CLI/MCP 分别连接和认证；search/scrape/interact 各自功能与计费能力 |
| claude-mem | worker 和各项 MCP 工具在安装版本中的实际可用性 |
| 课程平台 | 题目和截止信息准确，提交状态有平台证据；上传/提交另需用户授权 |
| hooks / 循环 | 宿主事件和路径、停止条件、退出与资源清理；归档中的流程不启用 |

此轮不因验证需要而上传本地文档、安装全局依赖、改动真实宏配置、注册 hooks 或执行课程提交。历史 `test-env/` 内容未随仓库发布，不能作为读者可复现的当前验收证据。
