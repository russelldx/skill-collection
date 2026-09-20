# 交接文档 · 代码规范章节模板

> 编程项目专用：仅编程/开发任务的交接文档加载本模板，其他领域忽略。跨会话/多批次开发时，在交接文档中固定维护"代码规范"章节。每次代码审查后追加审查记录；新会话动代码前先读本节。

## 一、代码规范要求（新代码强制）

- **日志**：一律 `org.slf4j.Logger`（`LoggerFactory.getLogger(Xxx.class)`），禁止 `e.printStackTrace()`
- **资源关闭**：流/Writer 用 try-with-resources；EasyExcel `ExcelReader` 用后 `finally { reader.finish(); }`
- **import**：禁止通配符 `*`（`java.util.*`、`dao.*` 等），逐个展开实际用到的类
- **异常处理**：Controller 层统一捕获并返回 ResultJson；日志记录参数上下文（如 `log.error("xxx失败, key={}", key, e)`）
- **重复代码**：相同逻辑（如取登录用户）提取私有方法，禁止 3 处以上复制
- **无意义代码**：不写多余的 URLDecoder.decode（路径拼接不需要）、不写注释掉的死代码
- **注释**：注释说明 WHY 不说明 WHAT；类注释中的文件名/表名必须与实际一致（模板名/表名改了就同步改）

## 二、代码审查模式（PUA · Jobs 味：减法优先 + 像素级完美）

审查顺序（每轮必走）：
1. **资源审计**：流/连接/Writer 是否关闭（try-with-resources）？EasyExcel reader 是否 finish？
2. **日志审计**：printStackTrace 残留？Logger 是否带参数上下文？
3. **重复审计**：同类 try-catch 是否 ≥3 处 → 提取方法
4. **import 审计**：通配符 → 展开
5. **正确性审计**：边界输入（空值/空格/特殊字符）→ trim + 显式校验；事务方法内返回 error 不回滚的行为要披露
6. **注释审计**：文件名/表名/业务描述与实际一致

审查记录格式（追加到交接文档）：
```
### 审查 N：<日期> <范围>
- [问题] 现象 → 修复动作 → 涉及文件
- [保留] 行为决策（如：部分成功不回滚，与旧接口一致）
```

## 三、环境红线

- 本地 Maven 仓库（如 `D:/develop/apache-maven-3.6.3/mvn_repo`）是 IDEA 可编译的环境基线，**禁止覆盖/替换其中的框架 jar**；如因命令行编译临时替换，**必须恢复原状**并在交接文档记录
- 命令行 mvn 与 IDEA 编译环境不一致时（依赖版本/仓库差异），以 IDEA 编译为准，不要用命令行结果否定 IDEA
