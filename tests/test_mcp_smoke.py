"""Offline MCP smoke regression tests; never start a process or contact a server."""

import asyncio
from contextlib import asynccontextmanager, redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "mcp-smoke.py"
if SCRIPT.exists():
    SPEC = importlib.util.spec_from_file_location("mcp_smoke_under_test", SCRIPT)
    smoke = importlib.util.module_from_spec(SPEC)
    sys.modules[SPEC.name] = smoke
    SPEC.loader.exec_module(smoke)
else:
    smoke = None

from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool


SECRET = "fixture-secret-never-print"
PRIVATE_URL = "https://private.invalid/" + SECRET


def tool(name="list_pages", schema=None):
    return Tool(name=name, description=SECRET,
                inputSchema=schema if schema is not None else {"type": "object"})


class FakeSession:
    def __init__(self, pages=None, fail=None, hang=None, call_result=None):
        self.pages = pages if pages is not None else [ListToolsResult(tools=[tool()])]
        self.fail = fail
        self.hang = hang
        self.call_result = call_result or CallToolResult(content=[])
        self.events = []
        self.cursors = []
        self.calls = []

    async def step(self, name):
        self.events.append(name)
        if self.fail == name:
            raise RuntimeError(PRIVATE_URL)
        if self.hang == name:
            await asyncio.Event().wait()

    async def initialize(self):
        await self.step("initialize")
        return SimpleNamespace(capabilities=SimpleNamespace(tools=SimpleNamespace()))

    async def list_tools(self, cursor=None):
        await self.step("list_tools")
        self.cursors.append(cursor)
        return self.pages[min(len(self.cursors) - 1, len(self.pages) - 1)]

    async def call_tool(self, name, arguments):
        await self.step("call_tool")
        self.calls.append((name, arguments))
        return self.call_result


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(smoke, "approved mcp-smoke.py CLI has not been implemented")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name) / "private-config.json"
        self.write_config({"command": sys.executable})

    def write_config(self, entry, others=None):
        entries = {"chosen": entry}
        entries.update(others or {})
        self.config.write_text(json.dumps({"mcpServers": entries}), encoding="utf-8")

    def cli(self, *extra, session=None, env=None):
        session = session or FakeSession()

        @asynccontextmanager
        async def connection(plan, timeout):
            session.events.append("open")
            try:
                # Model SDK task-group scope ordering; all entry/exit stays in one task.
                import anyio
                async with anyio.create_task_group():
                    yield session
            finally:
                await asyncio.sleep(0)
                session.events.append("close")

        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(smoke, "open_session", connection), \
                patch.dict(os.environ, env or {}, clear=False), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            status = smoke.main(["--config", str(self.config), "--server", "chosen", *extra])
        self.assertEqual(stderr.getvalue(), "")
        result = json.loads(stdout.getvalue())
        for sensitive in (SECRET, "private.invalid", self.temp.name, "private-config.json"):
            self.assertNotIn(sensitive, stdout.getvalue())
        self.assertEqual(status == 0, result["result"] in ("passed", "preflight_passed"))
        return result, session

    def assert_failure(self, result, code):
        self.assertEqual(result["result"], "failed")
        self.assertEqual(result["code"], code)

    def test_default_is_static_selected_project_evidence_only(self):
        self.write_config({"command": sys.executable}, {"other": {"command": "npx", "args": ["-y", SECRET]}})
        result, session = self.cli()
        self.assertEqual(result["result"], "preflight_passed")
        self.assertEqual(result["server"], "chosen")
        self.assertEqual(result["transport"], "stdio")
        self.assertEqual(result["evidence"], "project_config_only")
        self.assertEqual(result["host_active_tools"], "not_checked")
        self.assertEqual(result["config"]["path"], "<project-config>")
        self.assertEqual(len(result["config"]["sha256"]), 64)
        self.assertEqual(session.events, [])

    def test_malformed_config_shapes_and_duplicate_keys(self):
        for content in ("{", "[]", "{}", '{"mcpServers":[]}',
                        '{"mcpServers":{"chosen":null}}',
                        '{"mcpServers":{},"mcpServers":{}}'):
            with self.subTest(content=content):
                self.config.write_text(content, encoding="utf-8")
                result, session = self.cli()
                self.assert_failure(result, "invalid_config")
                self.assertEqual(session.events, [])

    def test_missing_file_server_command_and_dependency(self):
        self.config.unlink()
        result, _ = self.cli()
        self.assert_failure(result, "config_unreadable")
        self.config.write_text('{"mcpServers":{}}', encoding="utf-8")
        result, _ = self.cli()
        self.assert_failure(result, "server_not_found")
        self.write_config({"type": "stdio"})
        result, _ = self.cli()
        self.assert_failure(result, "missing_command")
        self.write_config({"command": "definitely-not-installed-fixture-program"})
        result, _ = self.cli("--connect")
        self.assert_failure(result, "missing_dependency")
        self.assertEqual(result["missing_dependencies"], ["executable"])

    def test_missing_sdk_dependency_is_sanitized(self):
        with patch.object(smoke, "load_sdk", side_effect=ImportError(SECRET)):
            result, session = self.cli("--connect")
        self.assert_failure(result, "missing_dependency")
        self.assertEqual(result["missing_dependencies"], ["mcp"])
        self.assertEqual(session.events, [])

    def test_invalid_entries_do_not_launch(self):
        entries = [
            {"command": sys.executable, "args": "not an array"},
            {"command": sys.executable, "args": [5]},
            {"command": sys.executable, "env": {"TOKEN": 12}},
            {"command": sys.executable, "env": {"BAD=KEY": "value"}},
            {"command": sys.executable, "disabled": True},
            {"command": sys.executable, "url": PRIVATE_URL},
            {"type": "http", "url": PRIVATE_URL, "command": sys.executable},
            {"type": "websocket", "url": PRIVATE_URL},
            {"url": PRIVATE_URL},
            {"type": "http", "url": PRIVATE_URL, "headers": []},
            {"type": "http", "url": PRIVATE_URL, "headers": {"Authorization": "line\nbreak"}},
            {"type": "http", "url": "https://user:password@private.invalid/"},
            {"type": "http", "url": "file:///private"},
            {"type": "http", "url": "http://private.invalid/"},
            {"command": sys.executable, "unknown_security_option": "value"},
        ]
        for entry in entries:
            with self.subTest(entry=entry):
                self.write_config(entry)
                result, session = self.cli("--connect")
                self.assertEqual(result["result"], "failed")
                self.assertEqual(session.events, [])

    def test_missing_and_unexpanded_env_fail_closed(self):
        for value in ("${SMOKE_ABSENT}", "${BROKEN", "${TOKEN:-default}", "${NESTED}"):
            for field in ("args", "env", "headers", "url", "command"):
                with self.subTest(field=field, value=value):
                    if field in ("headers", "url"):
                        entry = {"type": "http", "url": PRIVATE_URL}
                        entry[field] = {"Authorization": value} if field == "headers" else "https://" + value
                    else:
                        entry = {"command": sys.executable}
                        entry[field] = {"TOKEN": value} if field == "env" else [value] if field == "args" else value
                    self.write_config(entry)
                    with patch.dict(os.environ, {"NESTED": "${STILL_LITERAL}"}, clear=True):
                        result, session = self.cli("--connect")
                    self.assertIn(result["code"], ("missing_environment", "unexpanded_environment"))
                    self.assertEqual(session.events, [])

    def test_exact_expansion_preserves_argument_boundaries_without_global_mutation(self):
        arguments = ["${VALUE}", "prefix-${VALUE}-suffix", "a; $(touch not-run) & | > file", "two words"]
        self.write_config({"command": sys.executable, "args": arguments, "env": {"TOKEN": "${VALUE}"}})
        with patch.dict(os.environ, {"VALUE": SECRET}, clear=False):
            before = dict(os.environ)
            plan = smoke.load_plan(self.config, "chosen")
            self.assertEqual(plan.args, [SECRET, "prefix-" + SECRET + "-suffix", *arguments[2:]])
            self.assertEqual(plan.env, {"TOKEN": SECRET})
            self.assertEqual(dict(os.environ), before)
            result, _ = self.cli()
        self.assertEqual(result["result"], "preflight_passed")

    def test_download_runners_and_shell_wrappers_blocked(self):
        commands = ("npx", "npx.cmd", "npm", "pnpm", "yarn", "uvx", "uv", "cmd.exe", "powershell.exe", "bash", "sh", "env")
        for command in commands:
            for args in (["-y", "server@latest"], ["--no-install", "server"]):
                with self.subTest(command=command, args=args):
                    self.write_config({"command": command, "args": args})
                    result, session = self.cli("--connect")
                    self.assert_failure(result, "unsafe_launcher")
                    self.assertEqual(session.events, [])

    def test_override_replaces_entire_npx_launch_not_only_executable(self):
        self.write_config({"command": "npx", "args": ["-y", "server@latest"], "env": {"TOKEN": "${VALUE}"}})
        with patch.dict(os.environ, {"VALUE": SECRET}):
            plan = smoke.load_plan(self.config, "chosen", command=sys.executable, command_args=["installed-server.py"])
            self.assertEqual(plan.args, ["installed-server.py"])
            self.assertEqual(Path(plan.command).resolve(), Path(sys.executable).resolve())
            self.assertEqual(plan.env, {"TOKEN": SECRET})
            result, _ = self.cli("--command", sys.executable, "--command-args", '["installed-server.py"]')
            self.assertEqual(result["result"], "preflight_passed")
            self.assertEqual(result["evidence"], "project_config_with_launch_override")
            result, session = self.cli("--command", sys.executable)
            self.assert_failure(result, "invalid_cli")
            self.assertEqual(session.events, [])

    def test_http_and_sse_static_checks_never_connect(self):
        for transport in ("http", "streamable-http", "streamable_http", "sse"):
            self.write_config({"type": transport, "url": PRIVATE_URL, "headers": {"Authorization": "Bearer ${VALUE}"}})
            result, session = self.cli(env={"VALUE": SECRET})
            self.assertEqual(result["transport"], "sse" if transport == "sse" else "http")
            self.assertEqual(result["result"], "preflight_passed")
            self.assertEqual(session.events, [])

    def test_connect_initializes_paginates_and_closes(self):
        pages = [ListToolsResult(tools=[tool()], nextCursor=SECRET), ListToolsResult(tools=[tool("list_corpora")])]
        result, session = self.cli("--connect", "--require-tool", "list_corpora", session=FakeSession(pages))
        self.assertEqual(result["result"], "passed")
        self.assertEqual(result["tool_count"], 2)
        self.assertEqual(result["pages"], 2)
        self.assertEqual(session.cursors, [None, SECRET])
        self.assertEqual(session.events, ["open", "initialize", "list_tools", "list_tools", "close"])
        self.assertIn({"step": "cleanup", "result": "ok"}, result["steps"])

    def test_repeated_cursor_and_page_limit_stop(self):
        result, session = self.cli("--connect", session=FakeSession([ListToolsResult(tools=[tool()], nextCursor=SECRET)]))
        self.assert_failure(result, "repeated_cursor")
        self.assertEqual(len(session.cursors), 2)
        self.assertEqual(session.events[-1], "close")
        pages = [ListToolsResult(tools=[tool("tool_" + str(i))], nextCursor=str(i)) for i in range(100)]
        result, session = self.cli("--connect", "--max-pages", "2", session=FakeSession(pages))
        self.assert_failure(result, "page_limit")
        self.assertEqual(len(session.cursors), 2)

    def test_empty_missing_malformed_and_duplicate_tools_fail(self):
        cases = [([ListToolsResult(tools=[])], [], "empty_tools"),
                 ([ListToolsResult(tools=[tool()])], ["--require-tool", "absent"], "missing_tools"),
                 ([SimpleNamespace(nextCursor=None)], [], "invalid_tools"),
                 ([ListToolsResult(tools=[tool(schema={})])], [], "invalid_schema"),
                 ([ListToolsResult(tools=[tool(), tool()])], [], "duplicate_tool")]
        for pages, args, code in cases:
            result, session = self.cli("--connect", *args, session=FakeSession(pages))
            self.assert_failure(result, code)
            self.assertEqual(session.events[-1], "close")

    def test_timeout_and_failure_cleanup_at_each_protocol_step(self):
        for step in ("initialize", "list_tools", "call_tool"):
            args = ["--connect", "--timeout", "0.02"]
            if step == "call_tool":
                args += ["--call", "list_pages", "--arguments", "{}"]
            for kind, code in (("hang", "timeout"), ("fail", "runtime_error")):
                with self.subTest(step=step, kind=kind):
                    result, session = self.cli(*args, session=FakeSession(**{kind: step}))
                    self.assert_failure(result, code)
                    self.assertEqual(session.events[-1], "close")

    def test_call_is_allowlisted_requires_connect_and_explicit_empty_arguments(self):
        for args in (["--call", "list_pages", "--arguments", "{}"],
                     ["--connect", "--call", "list_pages"],
                     ["--connect", "--call", "evaluate_script", "--arguments", "{}"],
                     ["--connect", "--call", "list_pages", "--arguments", "[]"],
                     ["--connect", "--call", "list_pages", "--arguments", '{"code":"private"}'],
                     ["--connect", "--arguments", "{}"]):
            result, session = self.cli(*args)
            self.assert_failure(result, "invalid_cli")
            self.assertEqual(session.events, [])

    def test_allowlisted_calls_keep_iserror_and_conservatively_check_text_errors(self):
        for name in ("list_pages", "list_corpora"):
            for is_error, text, code in ((False, "ok " + SECRET, None),
                                         (True, SECRET, "tool_error"),
                                         (False, "Error: " + SECRET, "tool_text_error"),
                                         (False, '{"error":"' + SECRET + '"}', "tool_text_error")):
                result, session = self.cli("--connect", "--call", name, "--arguments", "{}", session=FakeSession(
                    pages=[ListToolsResult(tools=[tool(name)])],
                    call_result=CallToolResult(isError=is_error, content=[TextContent(type="text", text=text)])))
                if code:
                    self.assert_failure(result, code)
                else:
                    self.assertEqual(result["result"], "passed")
                self.assertEqual(session.calls, [(name, {})])
                self.assertEqual(session.events[-1], "close")

    def test_call_checks_required_schema_without_executing(self):
        schema = {"type": "object", "properties": {"account": {"type": "string"}}, "required": ["account"]}
        result, session = self.cli("--connect", "--call", "list_pages", "--arguments", "{}", session=FakeSession(
            pages=[ListToolsResult(tools=[tool(schema=schema)])]))
        self.assert_failure(result, "call_schema_not_supported")
        self.assertEqual(session.calls, [])

    def test_invalid_cli_and_timeout_values_emit_only_metadata(self):
        for args in (["--timeout", "nan"], ["--timeout", "inf"], ["--timeout", "0"],
                     ["--timeout", "-1"], ["--max-pages", "0"], ["--max-pages", "10001"],
                     ["--unknown", SECRET], ["--server", PRIVATE_URL]):
            result, session = self.cli(*args)
            self.assert_failure(result, "invalid_cli")
            self.assertEqual(session.events, [])
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = smoke.main([])
        self.assertNotEqual(status, 0)
        self.assertEqual(json.loads(out.getvalue())["code"], "invalid_cli")
        self.assertEqual(err.getvalue(), "")

    def test_missing_capability_and_invalid_cursor_fail_after_cleanup(self):
        session = FakeSession()

        async def no_tools():
            return SimpleNamespace(capabilities=SimpleNamespace(tools=None))

        session.initialize = no_tools
        result, session = self.cli("--connect", session=session)
        self.assert_failure(result, "missing_tools_capability")
        self.assertEqual(session.cursors, [])
        self.assertEqual(session.events[-1], "close")
        for cursor in ("", 5, []):
            result, session = self.cli("--connect", session=FakeSession([
                SimpleNamespace(tools=[tool()], nextCursor=cursor)]))
            self.assert_failure(result, "invalid_cursor")
            self.assertEqual(session.events[-1], "close")

    def test_blank_command_and_http_command_args_override_are_rejected(self):
        self.write_config({"command": "   "})
        result, _ = self.cli()
        self.assertEqual(result["result"], "failed")
        self.write_config({"type": "http", "url": PRIVATE_URL})
        with self.assertRaises(smoke.SmokeError):
            smoke.load_plan(self.config, "chosen", command_args=[])

    def test_runtime_diagnostics_do_not_escape_and_logging_is_restored(self):
        session = FakeSession()

        async def noisy_initialize():
            print(SECRET)
            print(PRIVATE_URL, file=sys.stderr)
            logging.error(SECRET)
            raise RuntimeError(PRIVATE_URL)

        session.initialize = noisy_initialize
        previous = logging.root.manager.disable
        result, _ = self.cli("--connect", session=session)
        self.assert_failure(result, "runtime_error")
        self.assertEqual(logging.root.manager.disable, previous)


class SDKWiringTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.assertIsNotNone(smoke, "approved mcp-smoke.py CLI has not been implemented")

    async def test_real_sdk_parameters_fake_transports_and_session_lifetime(self):
        sdk = smoke.load_sdk()
        for transport in ("stdio", "http", "sse"):
            events, captured = [], {}
            read, write = object(), object()

            @asynccontextmanager
            async def fake_transport(*args, **kwargs):
                captured["transport"] = (args, kwargs)
                events.append("transport_enter")
                try:
                    yield (read, write) if transport == "stdio" else (read, write, lambda: SECRET)
                finally:
                    events.append("transport_exit")

            @asynccontextmanager
            async def fake_session(*args, **kwargs):
                self.assertEqual(args, (read, write))
                captured["session"] = kwargs
                events.append("session_enter")
                try:
                    yield FakeSession()
                finally:
                    events.append("session_exit")

            @asynccontextmanager
            async def fake_http(**kwargs):
                captured["http"] = kwargs
                events.append("http_enter")
                try:
                    yield object()
                finally:
                    events.append("http_exit")

            fake_sdk = SimpleNamespace(**vars(sdk))
            fake_sdk.ClientSession = fake_session
            fake_sdk.stdio_client = fake_transport
            fake_sdk.sse_client = fake_transport
            fake_sdk.streamable_http_client = fake_transport
            fake_sdk.AsyncClient = fake_http
            plan = smoke.Plan(transport=transport, command=sys.executable,
                              args=["a & b", "two words"], env={"TOKEN": SECRET},
                              cwd=str(ROOT), url=PRIVATE_URL, headers={"Authorization": SECRET})
            with patch.object(smoke, "load_sdk", return_value=fake_sdk):
                async with smoke.open_session(plan, 2):
                    events.append("body")
            self.assertLess(events.index("session_exit"), events.index("transport_exit"))
            self.assertEqual(captured["session"]["read_timeout_seconds"].total_seconds(), 2)
            args, kwargs = captured["transport"]
            if transport == "stdio":
                params = args[0]
                self.assertIsInstance(params, sdk.StdioServerParameters)
                self.assertEqual(params.args, ["a & b", "two words"])
                self.assertEqual(params.env, {"TOKEN": SECRET})
                self.assertEqual(kwargs["errlog"].name, os.devnull)
                self.assertTrue(kwargs["errlog"].closed)
                self.assertNotIn("shell", kwargs)
            elif transport == "http":
                self.assertEqual(captured["http"]["headers"], {"Authorization": SECRET})
                self.assertFalse(captured["http"]["trust_env"])
                self.assertFalse(captured["http"]["follow_redirects"])
                self.assertLess(events.index("transport_exit"), events.index("http_exit"))
            else:
                self.assertEqual(kwargs["headers"], {"Authorization": SECRET})
                self.assertEqual(kwargs["sse_read_timeout"], 2)
                self.assertIn("httpx_client_factory", kwargs)

    async def test_partial_session_entry_closes_transport(self):
        sdk = smoke.load_sdk()
        events = []

        @asynccontextmanager
        async def transport(*args, **kwargs):
            try:
                yield object(), object()
            finally:
                events.append("closed")

        def session(*args, **kwargs):
            raise RuntimeError(SECRET)

        fake = SimpleNamespace(**vars(sdk))
        fake.stdio_client, fake.ClientSession = transport, session
        plan = smoke.Plan(transport="stdio", command=sys.executable)
        with patch.object(smoke, "load_sdk", return_value=fake):
            with self.assertRaises(RuntimeError):
                async with smoke.open_session(plan, 1):
                    self.fail("failed entry must not yield")
        self.assertEqual(events, ["closed"])

    async def test_entry_timeout_and_slow_cleanup_are_bounded(self):
        for phase in ("enter", "exit"):
            with self.subTest(phase=phase):
                sdk = smoke.load_sdk()
                events = []

                @asynccontextmanager
                async def transport(*args, **kwargs):
                    try:
                        if phase == "enter":
                            await asyncio.Event().wait()
                        yield object(), object()
                    finally:
                        try:
                            if phase == "exit":
                                await asyncio.Event().wait()
                        finally:
                            events.append("closed")

                @asynccontextmanager
                async def session(*args, **kwargs):
                    yield FakeSession()

                sdk.stdio_client, sdk.ClientSession = transport, session
                plan = smoke.Plan(transport="stdio", command=sys.executable)
                options = SimpleNamespace(timeout=0.02, max_pages=2, require_tool=[], call=None)
                report = {"steps": []}
                with patch.object(smoke, "load_sdk", return_value=sdk), \
                        patch.object(smoke, "CLEANUP_TIMEOUT", 0.02):
                    async with asyncio.timeout(1):
                        with self.assertRaises(TimeoutError):
                            await smoke.probe(plan, options, report)
                self.assertEqual(events, ["closed"])
                self.assertNotIn({"step": "cleanup", "result": "ok"}, report["steps"])

    async def test_installed_sdk_session_initializes_and_lists_over_memory_streams(self):
        # Real SDK session/protocol types, fake peer in memory: no sockets/processes.
        import anyio
        from mcp.shared.message import SessionMessage
        from mcp.types import JSONRPCMessage, JSONRPCResponse
        sdk = smoke.load_sdk()
        events = []

        @asynccontextmanager
        async def transport(*args, **kwargs):
            to_client, client_read = anyio.create_memory_object_stream(10)
            client_write, from_client = anyio.create_memory_object_stream(10)

            async def peer():
                async with from_client, to_client:
                    async for message in from_client:
                        request = message.message.root
                        if not hasattr(request, "id"):
                            continue
                        events.append(request.method)
                        if request.method == "initialize":
                            result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}},
                                      "serverInfo": {"name": "fixture", "version": "1"}}
                        else:
                            result = {"tools": [tool().model_dump()]}
                        await to_client.send(SessionMessage(JSONRPCMessage(
                            JSONRPCResponse(jsonrpc="2.0", id=request.id, result=result))))

            async with client_read, client_write, anyio.create_task_group() as group:
                group.start_soon(peer)
                try:
                    yield client_read, client_write
                finally:
                    group.cancel_scope.cancel()
            events.append("closed")

        sdk.stdio_client = transport
        report = {"steps": []}
        options = SimpleNamespace(timeout=1, max_pages=2, require_tool=["list_pages"], call=None)
        with patch.object(smoke, "load_sdk", return_value=sdk):
            await smoke.probe(smoke.Plan(transport="stdio", command=sys.executable), options, report)
        self.assertEqual(events, ["initialize", "tools/list", "closed"])
        self.assertEqual(report["tool_count"], 1)
        self.assertIn({"step": "cleanup", "result": "ok"}, report["steps"])


if __name__ == "__main__":
    unittest.main()
