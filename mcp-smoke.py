#!/usr/bin/env python3
"""Selected MCP preflight and opt-in smoke checks; see MCP-SETUP.md for boundaries."""

import argparse
import asyncio
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from datetime import timedelta
import hashlib
from importlib.metadata import version
import ipaddress
import json
import logging
import math
import os
from pathlib import Path
import re
import shutil
from types import SimpleNamespace
from urllib.parse import urlsplit


NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}\Z")
ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
READ_ONLY_CALLS = frozenset({"list_pages", "list_corpora"})
BLOCKED_LAUNCHERS = frozenset({
    "npx", "npm", "pnpm", "pnpx", "yarn", "yarnpkg", "bun", "bunx", "uv", "uvx",
    "cmd", "powershell", "pwsh", "sh", "bash", "zsh", "fish", "dash", "env",
})
CLEANUP_TIMEOUT = 5.0


class SmokeError(Exception):
    """Only fixed, non-sensitive error codes cross the reporting boundary."""

    def __init__(self, code, dependencies=()):
        super().__init__(code)
        self.code = code
        self.dependencies = list(dependencies)


@dataclass(repr=False)
class Plan:
    transport: str
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("non-JSON constant")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)


def expand(value, environ):
    if not isinstance(value, str) or "\0" in value:
        raise SmokeError("invalid_config")

    def replacement(match):
        name = match.group(1)
        if name not in environ or not environ[name]:
            raise SmokeError("missing_environment")
        return environ[name]

    expanded = ENV_REF.sub(replacement, value)
    if "${" in expanded:
        raise SmokeError("unexpanded_environment")
    if "\0" in expanded:
        raise SmokeError("invalid_config")
    return expanded


def string_map(value, environ, headers=False):
    if not isinstance(value, dict):
        raise SmokeError("invalid_config")
    result = {}
    for key, item in value.items():
        key_pattern = r"[!#$%&'*+.^_`|~0-9A-Za-z-]+" if headers else ENV_NAME
        if not isinstance(key, str) or not re.fullmatch(key_pattern, key):
            raise SmokeError("invalid_config")
        expanded = expand(item, environ)
        if headers and any(ord(char) < 32 or ord(char) == 127 for char in expanded):
            raise SmokeError("invalid_config")
        result[key] = expanded
    return result


def check_launcher(command):
    name = command.replace("\\", "/").rsplit("/", 1)[-1].lower()
    stem, extension = os.path.splitext(name)
    if name in BLOCKED_LAUNCHERS or stem in BLOCKED_LAUNCHERS or extension in {".cmd", ".bat", ".ps1"}:
        raise SmokeError("unsafe_launcher")


def load_plan(config_path, server, *, command=None, command_args=None, report=None):
    """Read exactly one supplied project file and select exactly one entry."""
    path = Path(config_path).resolve()
    if report is not None:
        report["config"] = {
            "path": "<project-config>",
            "path_sha256": hashlib.sha256(str(path).encode("utf-8")).hexdigest(),
        }
    try:
        with path.open("rb") as stream:
            raw = stream.read(1024 * 1024 + 1)
    except OSError:
        raise SmokeError("config_unreadable") from None
    if report is not None:
        report["config"]["sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        if len(raw) > 1024 * 1024:
            raise ValueError("oversized config")
        config = strict_json(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeError, RecursionError):
        raise SmokeError("invalid_config") from None
    if not isinstance(config, dict) or not isinstance(config.get("mcpServers"), dict):
        raise SmokeError("invalid_config")
    if server not in config["mcpServers"]:
        raise SmokeError("server_not_found")
    entry = config["mcpServers"][server]
    if not isinstance(entry, dict):
        raise SmokeError("invalid_config")
    allowed = {"type", "transport", "command", "args", "env", "cwd", "url", "headers", "disabled"}
    if entry.keys() - allowed or entry.get("disabled", False) is not False:
        raise SmokeError("invalid_config")
    transport = entry.get("type", entry.get("transport", "stdio"))
    aliases = {"stdio": "stdio", "http": "http", "streamable-http": "http", "streamable_http": "http", "sse": "sse"}
    if not isinstance(transport, str) or transport not in aliases:
        raise SmokeError("invalid_config")
    if "type" in entry and "transport" in entry and entry["type"] != entry["transport"]:
        raise SmokeError("invalid_config")
    transport = aliases[transport]
    if report is not None:
        report["transport"] = transport
    environ = dict(os.environ)  # No dotenv / host configuration reads; no global updates.
    if (command is None) != (command_args is None):
        raise SmokeError("invalid_cli")
    if transport == "stdio":
        if "url" in entry or "headers" in entry:
            raise SmokeError("invalid_config")
        selected_command = entry.get("command") if command is None else command
        if not selected_command:
            raise SmokeError("missing_command")
        selected_command = expand(selected_command, environ)
        args = entry.get("args", []) if command is None else command_args
        if not isinstance(args, list):
            raise SmokeError("invalid_config")
        args = [expand(arg, environ) for arg in args]
        env = string_map(entry.get("env", {}), environ)
        cwd = Path(expand(entry.get("cwd", str(path.parent)), environ))
        if not cwd.is_absolute():
            cwd = path.parent / cwd
        cwd = cwd.resolve()
        if not cwd.is_dir():
            raise SmokeError("invalid_cwd")
        check_launcher(selected_command)
        if "/" in selected_command or "\\" in selected_command:
            executable = Path(selected_command)
            if not executable.is_absolute():
                executable = cwd / executable
            selected_command = str(executable.resolve())
        resolved = shutil.which(selected_command, path=env.get("PATH", environ.get("PATH", os.defpath)))
        if not resolved:
            raise SmokeError("missing_dependency", ["executable"])
        resolved = str(Path(resolved).resolve())
        check_launcher(resolved)
        return Plan(transport, resolved, args, env, str(cwd))
    if any(key in entry for key in ("command", "args", "env", "cwd")) or command is not None:
        raise SmokeError("invalid_config")
    url = expand(entry.get("url"), environ)
    try:
        parsed = urlsplit(url)
        if not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.fragment:
            raise ValueError("invalid endpoint")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("invalid port")
        if any(char.isspace() or ord(char) < 32 for char in url):
            raise ValueError("invalid endpoint")
        loopback = parsed.hostname == "localhost"
        try:
            loopback = loopback or ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            pass
        if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
            raise ValueError("TLS required except on loopback")
    except ValueError:
        raise SmokeError("invalid_url") from None
    return Plan(transport, url=url, headers=string_map(entry.get("headers", {}), environ, headers=True))


def load_sdk():
    # Verified against the installed 1.27.1 APIs, not copied from newer docs.
    from httpx import AsyncClient, Timeout
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.sse import sse_client
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamable_http_client
    return SimpleNamespace(ClientSession=ClientSession, StdioServerParameters=StdioServerParameters,
                           stdio_client=stdio_client, sse_client=sse_client,
                           streamable_http_client=streamable_http_client,
                           AsyncClient=AsyncClient, Timeout=Timeout, version=version("mcp"))


@asynccontextmanager
async def open_session(plan, timeout):
    """Enter and unwind all SDK contexts in the same task, including partial entry."""
    sdk = load_sdk()
    stack = AsyncExitStack()
    try:
        if plan.transport == "stdio":
            errlog = stack.enter_context(open(os.devnull, "w", encoding="utf-8"))
            params = sdk.StdioServerParameters(command=plan.command, args=plan.args, env=plan.env, cwd=plan.cwd)
            context = sdk.stdio_client(params, errlog=errlog)
        elif plan.transport == "http":
            client = await stack.enter_async_context(sdk.AsyncClient(
                headers=plan.headers, timeout=sdk.Timeout(timeout),
                follow_redirects=False, trust_env=False,
            ))
            context = sdk.streamable_http_client(plan.url, http_client=client)
        else:
            def http_factory(headers=None, timeout=None, auth=None):
                return sdk.AsyncClient(headers=headers, timeout=timeout, auth=auth,
                                       follow_redirects=False, trust_env=False)
            context = sdk.sse_client(plan.url, headers=plan.headers, timeout=timeout,
                                     sse_read_timeout=timeout, httpx_client_factory=http_factory)
        streams = await stack.enter_async_context(context)
        session = await stack.enter_async_context(sdk.ClientSession(
            streams[0], streams[1], read_timeout_seconds=timedelta(seconds=timeout),
        ))
        yield session
    finally:
        # asyncio deadlines do not introduce AnyIO cancel scopes around SDK exits.
        # Do not move stack.aclose into a different task (e.g. wait_for/shield).
        async with asyncio.timeout(CLEANUP_TIMEOUT):
            await stack.aclose()


def checked(report, step):
    report["steps"].append({"step": step, "result": "ok"})


def validate_schema(schema):
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise SmokeError("invalid_schema")
    if not isinstance(schema.get("properties", {}), dict):
        raise SmokeError("invalid_schema")
    required = schema.get("required", [])
    if not isinstance(required, list) or any(not isinstance(key, str) for key in required):
        raise SmokeError("invalid_schema")


def validate_call_schema(tool):
    schema = tool.inputSchema
    # A deliberately small subset sufficient to prove {} needs no required inputs.
    supported = {"type", "properties", "required", "additionalProperties", "$schema", "title", "description"}
    if schema.keys() - supported or schema.get("required"):
        raise SmokeError("call_schema_not_supported")
    annotations = getattr(tool, "annotations", None)
    if annotations is not None and getattr(annotations, "readOnlyHint", None) is False:
        raise SmokeError("call_schema_not_supported")


def text_error(text):
    if re.search(r"\b(error|failed|failure|exception|unauthorized|forbidden|denied)\b", text, re.I):
        return True
    try:
        value = strict_json(text)
    except (ValueError, RecursionError):
        return False
    return isinstance(value, dict) and (value.get("success") is False or value.get("isError") is True)


def check_call_result(result):
    if getattr(result, "isError", None) is True:
        raise SmokeError("tool_error")
    if getattr(result, "isError", None) is not False or not isinstance(getattr(result, "content", None), list):
        raise SmokeError("invalid_call_result")
    for content in result.content:
        if getattr(content, "type", None) == "text" and text_error(content.text):
            raise SmokeError("tool_text_error")
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict) and (structured.get("error") or structured.get("isError") is True or structured.get("success") is False):
        raise SmokeError("tool_text_error")


async def probe(plan, options, report):
    pending = None
    async with asyncio.timeout(options.timeout) as deadline:
        async with open_session(plan, options.timeout) as session:
            try:
                initialized = await session.initialize()
                if getattr(getattr(initialized, "capabilities", None), "tools", None) is None:
                    raise SmokeError("missing_tools_capability")
                checked(report, "initialize")
                tools, seen, cursor = {}, set(), None
                for page_number in range(1, options.max_pages + 1):
                    response = await session.list_tools(cursor=cursor)
                    page = getattr(response, "tools", None)
                    if not isinstance(page, list):
                        raise SmokeError("invalid_tools")
                    for tool in page:
                        name = getattr(tool, "name", None)
                        if not isinstance(name, str) or not name:
                            raise SmokeError("invalid_tools")
                        validate_schema(getattr(tool, "inputSchema", None))
                        if name in tools:
                            # Check cursor loops first, but never report a complete duplicate list.
                            if getattr(response, "nextCursor", None) in seen:
                                raise SmokeError("repeated_cursor")
                            raise SmokeError("duplicate_tool")
                        tools[name] = tool
                    report.update(pages=page_number, tool_count=len(tools))
                    cursor = getattr(response, "nextCursor", None)
                    if cursor is None:
                        break
                    if not isinstance(cursor, str) or not cursor:
                        raise SmokeError("invalid_cursor")
                    if cursor in seen:
                        raise SmokeError("repeated_cursor")
                    seen.add(cursor)
                else:
                    raise SmokeError("page_limit")
                if not tools:
                    raise SmokeError("empty_tools")
                checked(report, "list_tools")
                required = set(options.require_tool)
                if options.call:
                    required.add(options.call)
                if required - tools.keys():
                    raise SmokeError("missing_tools")
                checked(report, "tool_schemas")
                if required:
                    checked(report, "required_tools")
                if options.call:
                    validate_call_schema(tools[options.call])
                    result = await session.call_tool(options.call, arguments=options.arguments)
                    check_call_result(result)
                    checked(report, "read_only_call")
            except BaseException as exc:
                # Defer propagation until normal SDK cleanup (also on cancellation).
                pending = exc
            finally:
                if not deadline.expired():
                    deadline.reschedule(None)
        checked(report, "cleanup")
        if pending is not None:
            raise pending


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SmokeError("invalid_cli")


def parse_args(argv):
    parser = Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                    allow_abbrev=False)
    parser.add_argument("--config", required=True, help="explicit project JSON path; never auto-discovered")
    parser.add_argument("--server", required=True, help="one exact mcpServers entry")
    parser.add_argument("--connect", action="store_true", help="opt in to start/connect, initialize, and list tools")
    parser.add_argument("--timeout", type=float, default=15, help="total connection/protocol seconds (0 < n <= 300), plus up to 5s cleanup")
    parser.add_argument("--max-pages", type=int, default=100, help="finite list_tools page cap (1..1000)")
    parser.add_argument("--require-tool", action="append", default=[], help="exact required tool name; repeatable")
    parser.add_argument("--command", help="installed executable override, never a shell command string")
    parser.add_argument("--command-args", help="complete JSON argument array; required with --command")
    parser.add_argument("--call", choices=sorted(READ_ONLY_CALLS), help="optional read-only call; requires --connect --arguments '{}'")
    parser.add_argument("--arguments", help="explicit JSON object; v1 accepts only {}")
    options = parser.parse_args(argv)
    if not NAME.fullmatch(options.server) or any(not NAME.fullmatch(name) for name in options.require_tool):
        raise SmokeError("invalid_cli")
    if not math.isfinite(options.timeout) or not 0 < options.timeout <= 300 or not 1 <= options.max_pages <= 1000:
        raise SmokeError("invalid_cli")
    if (options.command is None) != (options.command_args is None):
        raise SmokeError("invalid_cli")
    try:
        if options.command_args is not None:
            options.command_args = strict_json(options.command_args)
            if not isinstance(options.command_args, list) or any(not isinstance(arg, str) for arg in options.command_args):
                raise ValueError("arguments must be strings")
        if options.call:
            if not options.connect or options.arguments is None:
                raise ValueError("explicit consent required")
            options.arguments = strict_json(options.arguments)
            if options.arguments != {}:
                raise ValueError("only empty arguments supported")
        elif options.arguments is not None:
            raise ValueError("call required")
    except (ValueError, RecursionError):
        raise SmokeError("invalid_cli") from None
    return options


@contextmanager
def private_diagnostics():
    # This standalone CLI never emits server stdout, stderr, SDK logs or exceptions.
    # Restore process-level diagnostics when invoked in tests / by an importer.
    previous = logging.root.manager.disable
    with open(os.devnull, "w", encoding="utf-8") as sink:
        try:
            logging.disable(logging.CRITICAL)
            with redirect_stdout(sink), redirect_stderr(sink):
                yield
        finally:
            logging.disable(previous)


def failure_details(error):
    if isinstance(error, SmokeError):
        return error
    if isinstance(error, TimeoutError):
        return SmokeError("timeout")
    if isinstance(error, BaseExceptionGroup):
        for child in error.exceptions:
            found = failure_details(child)
            if found.code != "runtime_error":
                return found
    return SmokeError("runtime_error")


def main(argv=None):
    report = {"server": None, "config": {"path": "<project-config>"}, "transport": None,
              "evidence": "project_config_only", "host_active_tools": "not_checked",
              "mode": "preflight", "steps": [], "result": "failed", "missing_dependencies": []}
    status = 1
    try:
        options = parse_args(argv)
        report.update(server=options.server, mode="connect" if options.connect else "preflight")
        if options.command is not None:
            report["evidence"] = "project_config_with_launch_override"
        with private_diagnostics():
            plan = load_plan(options.config, options.server, command=options.command,
                             command_args=options.command_args, report=report)
            checked(report, "config")
            checked(report, "environment")
            try:
                sdk = load_sdk()
            except ImportError:
                raise SmokeError("missing_dependency", ["mcp"]) from None
            report["sdk_version"] = sdk.version
            checked(report, "dependencies")
            if options.connect:
                asyncio.run(probe(plan, options, report))
                report.update(result="passed", code="runtime_checked")
            else:
                report.update(result="preflight_passed", code="static_only")
        status = 0
    except KeyboardInterrupt:
        report.update(code="interrupted")
        status = 130
    except Exception as exc:
        error = failure_details(exc)
        report.update(code=error.code, missing_dependencies=error.dependencies)
    # Whitelisted metadata only: never serialize config entries or exception messages.
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
