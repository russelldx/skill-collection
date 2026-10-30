// Window control for the privacy-preserving capture path.
//
// Snipaste's free build ignores --active-window, so the only way to keep a
// screenshot inside one application is to arrange that window, read its exact
// visible rectangle, capture it with "--area", and prove that nothing else is
// inside the rectangle. All Win32 work happens in one PowerShell script per
// call: the C# helpers are compiled once by Add-Type, which costs a few hundred
// milliseconds, so each call batches everything it needs.

import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const execFileAsync = promisify(execFile);

export const WINDOW_CONTROL = process.platform === 'win32';

const PS_SCRIPT = String.raw`
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)

Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;

public class WinInfo
{
    public long hwnd;
    public int pid;
    public string app;
    public string title;
    public int left;
    public int top;
    public int width;
    public int height;
    public bool maximized;
    public bool minimized;
    public bool foreground;
}

public static class SnipWin
{
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }

    [StructLayout(LayoutKind.Sequential)]
    public struct POINT { public int X; public int Y; }

    [StructLayout(LayoutKind.Sequential)]
    public struct WINDOWPLACEMENT
    {
        public int length;
        public int flags;
        public int showCmd;
        public POINT ptMinPosition;
        public POINT ptMaxPosition;
        public RECT rcNormalPosition;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct MONITORINFO
    {
        public int cbSize;
        public RECT rcMonitor;
        public RECT rcWork;
        public int dwFlags;
    }

    public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumProc cb, IntPtr lParam);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetWindowTextW(IntPtr hWnd, StringBuilder text, int max);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetWindowTextLengthW(IntPtr hWnd);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
    [DllImport("user32.dll")] private static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] private static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] private static extern bool GetWindowPlacement(IntPtr hWnd, ref WINDOWPLACEMENT placement);
    [DllImport("user32.dll")] private static extern bool ShowWindow(IntPtr hWnd, int cmd);
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] private static extern IntPtr WindowFromPoint(POINT point);
    [DllImport("user32.dll")] private static extern IntPtr GetAncestor(IntPtr hWnd, uint flags);
    [DllImport("user32.dll")] private static extern IntPtr MonitorFromWindow(IntPtr hWnd, uint flags);
    [DllImport("user32.dll")] private static extern bool GetMonitorInfo(IntPtr monitor, ref MONITORINFO info);
    [DllImport("dwmapi.dll")] private static extern int DwmGetWindowAttribute(IntPtr hWnd, int attribute, out RECT rect, int size);
    [DllImport("dwmapi.dll", EntryPoint = "DwmGetWindowAttribute")] private static extern int DwmGetWindowAttributeInt(IntPtr hWnd, int attribute, out int value, int size);
    [DllImport("user32.dll")] private static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] private static extern bool SetProcessDpiAwarenessContext(IntPtr context);
    [DllImport("user32.dll")] private static extern bool AttachThreadInput(uint attach, uint attachTo, bool doAttach);
    [DllImport("user32.dll")] private static extern bool BringWindowToTop(IntPtr hWnd);
    [DllImport("kernel32.dll")] private static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] private static extern bool SetWindowPos(IntPtr hWnd, IntPtr after, int x, int y, int cx, int cy, uint flags);
    [DllImport("user32.dll")] private static extern int GetWindowLongW(IntPtr hWnd, int index);
    [DllImport("user32.dll")] private static extern bool GetLayeredWindowAttributes(IntPtr hWnd, out uint key, out byte alpha, out uint flags);

    public static void Init()
    {
        try { if (SetProcessDpiAwarenessContext(new IntPtr(-4))) return; } catch { }
        try { SetProcessDPIAware(); } catch { }
    }

    public static string TitleOf(IntPtr hWnd)
    {
        int len = GetWindowTextLengthW(hWnd);
        if (len <= 0) return string.Empty;
        StringBuilder sb = new StringBuilder(len + 2);
        GetWindowTextW(hWnd, sb, sb.Capacity);
        return sb.ToString();
    }

    public static string AppOf(int pid)
    {
        try { return Process.GetProcessById(pid).ProcessName; } catch { return string.Empty; }
    }

    public static WINDOWPLACEMENT Placement(IntPtr hWnd)
    {
        WINDOWPLACEMENT wp = new WINDOWPLACEMENT();
        wp.length = Marshal.SizeOf(typeof(WINDOWPLACEMENT));
        GetWindowPlacement(hWnd, ref wp);
        return wp;
    }

    public static int ShowCmdOf(IntPtr hWnd)
    {
        return Placement(hWnd).showCmd;
    }

    public static List<WinInfo> List()
    {
        List<WinInfo> list = new List<WinInfo>();
        IntPtr foreground = GetForegroundWindow();
        if (foreground == IntPtr.Zero) foreground = TopWindow();
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam)
        {
            if (!IsWindowVisible(hWnd)) return true;
            WINDOWPLACEMENT wp = Placement(hWnd);
            bool minimized = wp.showCmd == 2;
            // A minimized window reports its rect at -32000ish; the placement's
            // normal rect is the useful one for callers picking a target.
            RECT r = minimized ? wp.rcNormalPosition : new RECT();
            if (!minimized && !GetWindowRect(hWnd, out r)) return true;
            if (r.Right <= r.Left || r.Bottom <= r.Top) return true;
            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);
            WinInfo info = new WinInfo();
            info.hwnd = hWnd.ToInt64();
            info.pid = (int)pid;
            info.app = AppOf((int)pid);
            info.title = TitleOf(hWnd);
            info.left = r.Left;
            info.top = r.Top;
            info.width = r.Right - r.Left;
            info.height = r.Bottom - r.Top;
            info.maximized = wp.showCmd == 3;
            info.minimized = minimized;
            info.foreground = hWnd == foreground;
            list.Add(info);
            return true;
        }, IntPtr.Zero);
        return list;
    }

    // DWM's extended frame is the part of the window the user actually sees;
    // GetWindowRect includes a few invisible border pixels that would otherwise
    // capture whatever sits behind the window.
    public static RECT VisibleFrame(IntPtr hWnd)
    {
        RECT r;
        int hr = DwmGetWindowAttribute(hWnd, 9, out r, Marshal.SizeOf(typeof(RECT)));
        if (hr != 0 || r.Right <= r.Left || r.Bottom <= r.Top)
        {
            if (!GetWindowRect(hWnd, out r)) r = new RECT();
        }
        return r;
    }

    public static RECT WorkAreaOf(IntPtr hWnd)
    {
        MONITORINFO mi = new MONITORINFO();
        mi.cbSize = Marshal.SizeOf(typeof(MONITORINFO));
        IntPtr monitor = MonitorFromWindow(hWnd, 2);
        if (!GetMonitorInfo(monitor, ref mi)) return new RECT();
        return mi.rcWork;
    }

    public static RECT WindowRect(IntPtr hWnd)
    {
        RECT r;
        if (!GetWindowRect(hWnd, out r)) r = new RECT();
        return r;
    }

    public static RECT PrimaryWorkArea()
    {
        MONITORINFO mi = new MONITORINFO();
        mi.cbSize = Marshal.SizeOf(typeof(MONITORINFO));
        IntPtr monitor = MonitorFromWindow(IntPtr.Zero, 1);
        if (!GetMonitorInfo(monitor, ref mi)) return new RECT();
        return mi.rcWork;
    }

    // SetWindowPos is the restore primitive: SetWindowPlacement makes some
    // WinForms modal dialogs receive a WM_CLOSE and quit, which is exactly the
    // kind of side effect a capture helper must never have.
    public static bool Place(IntPtr hWnd, int left, int top, int width, int height)
    {
        return SetWindowPos(hWnd, IntPtr.Zero, left, top, width, height, 0x0004 | 0x0010);
    }

    public static IntPtr RootAt(int x, int y)
    {
        POINT p = new POINT();
        p.X = x;
        p.Y = y;
        return GetAncestor(WindowFromPoint(p), 2);
    }

    public static IntPtr RootOf(IntPtr hWnd) { return GetAncestor(hWnd, 2); }

    public static IntPtr ForegroundHwnd() { return GetForegroundWindow(); }

    // GetForegroundWindow returns 0 when the caller has no visible console,
    // which is exactly how the bridge runs. The top of the z-order stands in:
    // the first restored, titled, non-tool window that is not always-on-top,
    // so a floating widget above everything does not masquerade as the one the
    // user is working in.
    public static IntPtr TopWindow()
    {
        IntPtr best = IntPtr.Zero;
        IntPtr widget = IntPtr.Zero;
        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam)
        {
            if (best != IntPtr.Zero) return false;
            if (!IsWindowVisible(hWnd)) return true;
            if (Placement(hWnd).showCmd == 2) return true;
            if (TitleOf(hWnd).Length == 0) return true;
            if ((GetWindowLongW(hWnd, -20) & 0x00000080) != 0) return true;
            RECT r;
            if (!GetWindowRect(hWnd, out r)) return true;
            if (r.Right - r.Left < 200 || r.Bottom - r.Top < 150) return true;
            if (IsTopmost(hWnd))
            {
                if (widget == IntPtr.Zero) widget = hWnd;
                return true;
            }
            best = hWnd;
            return false;
        }, IntPtr.Zero);
        return best != IntPtr.Zero ? best : widget;
    }

    // A DWM-cloaked window (another virtual desktop, a suspended UWP app) or a
    // fully transparent layered window paints nothing, so it must not count as
    // an obstacle: refusing there would blame a window the user cannot see.
    public static bool Invisible(IntPtr hWnd)
    {
        int cloak;
        if (DwmGetWindowAttributeInt(hWnd, 14, out cloak, sizeof(int)) == 0 && cloak != 0) return true;
        uint key;
        byte alpha;
        uint flags;
        if (GetLayeredWindowAttributes(hWnd, out key, out alpha, out flags) && (flags & 2) != 0 && alpha == 0) return true;
        return false;
    }

    public static int PidOf(IntPtr hWnd)
    {
        uint pid;
        GetWindowThreadProcessId(hWnd, out pid);
        return (int)pid;
    }

    public static bool Minimize(IntPtr hWnd) { return ShowWindow(hWnd, 6); }
    public static bool Show(IntPtr hWnd, int cmd) { return ShowWindow(hWnd, cmd); }

    public static bool IsTopmost(IntPtr hWnd)
    {
        return (GetWindowLongW(hWnd, -20) & 0x8) != 0;
    }

    // Raising the target above the user's own windows is what makes a capture
    // succeed while they keep working elsewhere; the caller must undo it.
    public static bool SetTopmost(IntPtr hWnd, bool on)
    {
        return SetWindowPos(hWnd, new IntPtr(on ? -1 : -2), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010);
    }
    public static bool Maximize(IntPtr hWnd) { return ShowWindow(hWnd, 3); }
    public static bool Restore(IntPtr hWnd) { return ShowWindow(hWnd, 9); }
    public static bool Visible(IntPtr hWnd) { return IsWindowVisible(hWnd); }

    // A background process may not raise its own window while another app owns
    // the foreground. Attaching to that app's input queue lifts the lock for the
    // duration of the call; if the attach fails nothing is lost, the coverage
    // check simply reports what is actually visible.
    public static bool Activate(IntPtr hWnd)
    {
        if (SetForegroundWindow(hWnd)) return true;
        IntPtr fg = GetForegroundWindow();
        uint fgPid;
        uint fgThread = fg == IntPtr.Zero ? 0 : GetWindowThreadProcessId(fg, out fgPid);
        uint self = GetCurrentThreadId();
        bool attached = false;
        try
        {
            if (fgThread != 0 && fgThread != self) attached = AttachThreadInput(self, fgThread, true);
            BringWindowToTop(hWnd);
            SetForegroundWindow(hWnd);
            return GetForegroundWindow() == hWnd;
        }
        finally
        {
            if (attached) AttachThreadInput(self, fgThread, false);
        }
    }
}
'@

[SnipWin]::Init()

function To-Rect([int]$left, [int]$top, [int]$right, [int]$bottom) {
  [pscustomobject]@{
    left = $left
    top = $top
    width = [Math]::Max(0, $right - $left)
    height = [Math]::Max(0, $bottom - $top)
  }
}

function Select-Wins($wins) {
  if ($env:SNIP_HWND) {
    $want = [long]$env:SNIP_HWND
    return @($wins | Where-Object { [long]$_.hwnd -eq $want })
  }
  $appFilter = $env:SNIP_APP
  if ($appFilter) { $appFilter = ($appFilter -replace '\.exe$', '').ToLowerInvariant() }
  $titleFilter = $env:SNIP_TITLE
  $pidFilter = 0
  if ($env:SNIP_PID) { $pidFilter = [int]$env:SNIP_PID }
  $out = New-Object System.Collections.ArrayList
  foreach ($w in $wins) {
    if ($pidFilter -gt 0 -and $w.pid -ne $pidFilter) { continue }
    if ($appFilter -and ($w.app.ToLowerInvariant() -ne $appFilter)) { continue }
    if ($titleFilter -and ($w.title -notmatch $titleFilter)) { continue }
    if ((-not $w.title) -and $pidFilter -eq 0) { continue }
    [void]$out.Add($w)
  }
  return @($out)
}

function New-Rect([int]$left, [int]$top, [int]$width, [int]$height) {
  [pscustomobject]@{
    left = $left
    top = $top
    width = [int][Math]::Max(0, $width)
    height = [int][Math]::Max(0, $height)
  }
}

function Test-Coverage([long]$hwnd, [int]$procId, $rect) {
  $w = [int]$rect.width
  $h = [int]$rect.height
  if ($w -le 12 -or $h -le 12) {
    return [pscustomobject]@{ ok = $false; samples = 0; bad = 0; offender = 'the capture rectangle is too small to verify'; obstacles = @() }
  }
  $area = [double]$w * [double]$h
  $step = [int][Math]::Max(160, [Math]::Ceiling([Math]::Sqrt($area / 400.0)))
  $inset = 4
  $x0 = [int]$rect.left + $inset
  $y0 = [int]$rect.top + $inset
  $x1 = [int][Math]::Max($x0, [int]$rect.left + $w - $inset - 1)
  $y1 = [int][Math]::Max($y0, [int]$rect.top + $h - $inset - 1)
  $xs = New-Object System.Collections.ArrayList
  $x = $x0
  while ($x -lt $x1) { [void]$xs.Add($x); $x = $x + $step }
  [void]$xs.Add($x1)
  $ys = New-Object System.Collections.ArrayList
  $y = $y0
  while ($y -lt $y1) { [void]$ys.Add($y); $y = $y + $step }
  [void]$ys.Add($y1)
  $samples = 0
  $bad = 0
  $seen = @{}
  foreach ($px in $xs) {
    foreach ($py in $ys) {
      $samples++
      $root = [SnipWin]::RootAt([int]$px, [int]$py)
      if ($root.ToInt64() -eq $hwnd) { continue }
      $other = [SnipWin]::PidOf($root)
      if ($other -eq $procId) { continue }
      # Cloaked (other virtual desktop) and fully transparent windows are not
      # painted, so their points still show the target.
      if ([SnipWin]::Invisible($root)) { continue }
      $bad++
      $key = $root.ToInt64()
      if (-not $seen.ContainsKey($key)) {
        $name = ''
        try { $name = (Get-Process -Id $other -ErrorAction Stop).ProcessName } catch { $name = 'pid ' + $other }
        $winTitle = ''
        try { $winTitle = [SnipWin]::TitleOf($root) } catch { }
        $r = [SnipWin]::WindowRect($root)
        $seen[$key] = [pscustomobject]@{
          name = $name
          winTitle = $winTitle
          hits = 0
          minX = [int]$px
          maxX = [int]$px
          minY = [int]$py
          maxY = [int]$py
          window = (New-Rect $r.Left $r.Top ($r.Right - $r.Left) ($r.Bottom - $r.Top))
        }
      }
      $hit = $seen[$key]
      $hit.hits = $hit.hits + 1
      if ($px -lt $hit.minX) { $hit.minX = [int]$px }
      if ($px -gt $hit.maxX) { $hit.maxX = [int]$px }
      if ($py -lt $hit.minY) { $hit.minY = [int]$py }
      if ($py -gt $hit.maxY) { $hit.maxY = [int]$py }
    }
  }
  # The obstacle's own rectangle can be the whole screen even though only a
  # corner of it is painted (notification hosts use one big layered window), so
  # the extent used for trimming is the box around the points that actually hit
  # it, widened by half a grid step, and clipped to the window's own rectangle.
  $obstacles = @{}
  $margin = [int][Math]::Ceiling($step / 2.0)
  foreach ($key in $seen.Keys) {
    $hit = $seen[$key]
    $bx = $hit.minX - $margin
    $by = $hit.minY - $margin
    $br = $hit.maxX + $margin
    $bb = $hit.maxY + $margin
    $w = $hit.window
    $ix = [Math]::Max($bx, $w.left)
    $iy = [Math]::Max($by, $w.top)
    $ir = [Math]::Min($br, $w.left + $w.width)
    $ib = [Math]::Min($bb, $w.top + $w.height)
    if ($ir -gt $ix -and $ib -gt $iy) {
      $obstacles[$key] = New-Rect $ix $iy ($ir - $ix) ($ib - $iy)
    } else {
      $obstacles[$key] = New-Rect $bx $by ($br - $bx) ($bb - $by)
    }
  }
  $top = ''
  if ($seen.Count -gt 0) {
    $best = $seen.Values | Sort-Object -Property hits -Descending | Select-Object -First 1
    $top = $best.name
    if ($best.winTitle) { $top = $top + ' ("' + $best.winTitle + '")' }
  }
  return [pscustomobject]@{ ok = ($bad -eq 0); samples = $samples; bad = $bad; offender = $top; obstacles = @($obstacles.Values) }
}

function Test-Overlap($a, $b) {
  return (($b.left -lt ($a.left + $a.width)) -and (($b.left + $b.width) -gt $a.left) -and ($b.top -lt ($a.top + $a.height)) -and (($b.top + $b.height) -gt $a.top))
}

# A topmost widget (notification toast, music overlay, game launcher bar) can
# cover a corner of a maximized window without covering the content the caller
# cares about. Instead of refusing outright, cut the offending edges away and
# take the largest remaining rectangle that no foreign window touches. The
# result is always a sub-rectangle of what was asked for, so it can only leak
# less, never more.
function Get-CleanRect($base, $obstacles) {
  $baseArea = [double]$base.width * [double]$base.height
  $minWidth = 320
  $minHeight = 200
  $minShare = 0.6
  $best = $null
  $seen = @{}
  $frontier = @($base)
  for ($depth = 0; $depth -lt 4; $depth++) {
    $next = New-Object System.Collections.ArrayList
    foreach ($r in $frontier) {
      $hit = $null
      foreach ($o in $obstacles) {
        if (Test-Overlap $r $o) { $hit = $o; break }
      }
      if (-not $hit) {
        if ($r.width -ge $minWidth -and $r.height -ge $minHeight -and (([double]$r.width * $r.height) -ge ($minShare * $baseArea))) {
          if (($null -eq $best) -or (([double]$r.width * $r.height) -gt ([double]$best.width * $best.height))) { $best = $r }
        }
        continue
      }
      $cands = @(
        (New-Rect $r.left $r.top $r.width ([Math]::Min($r.height, $hit.top - $r.top))),
        (New-Rect $r.left ([Math]::Max($r.top, $hit.top + $hit.height)) $r.width ([Math]::Min($r.height, ($r.top + $r.height) - ($hit.top + $hit.height)))),
        (New-Rect $r.left $r.top ([Math]::Min($r.width, $hit.left - $r.left)) $r.height),
        (New-Rect ([Math]::Max($r.left, $hit.left + $hit.width)) $r.top ([Math]::Min($r.width, ($r.left + $r.width) - ($hit.left + $hit.width))) $r.height)
      )
      foreach ($c in $cands) {
        if ($c.width -lt $minWidth -or $c.height -lt $minHeight) { continue }
        $key = '' + $c.left + ',' + $c.top + ',' + $c.width + ',' + $c.height
        if ($seen.ContainsKey($key)) { continue }
        $seen[$key] = 1
        [void]$next.Add($c)
      }
    }
    if ($next.Count -eq 0) { break }
    $frontier = @($next)
  }
  return $best
}

function Invoke-List {
  $wins = @(Select-Wins @([SnipWin]::List()))
  $limit = 20
  if ($env:SNIP_LIMIT) { $limit = [int]$env:SNIP_LIMIT }
  $total = $wins.Count
  $sorted = @($wins | Sort-Object -Property @{ Expression = { $_.app }; Descending = $false }, @{ Expression = { $_.title }; Descending = $false } | Select-Object -First $limit)
  return [pscustomobject]@{ total = $total; windows = $sorted }
}

function Set-SavedPlacement([IntPtr]$hwnd, $saved) {
  $normal = $saved.normal
  $showCmd = [int]$saved.showCmd
  if ($showCmd -ne 1 -and $showCmd -ne 2 -and $showCmd -ne 3) { $showCmd = 1 }
  $nl = [int]$normal.left
  $nt = [int]$normal.top
  $nw = [int]$normal.width
  $nh = [int]$normal.height
  if ($nw -lt 80 -or $nh -lt 60) {
    $fallback = [SnipWin]::VisibleFrame($hwnd)
    $nl = $fallback.Left
    $nt = $fallback.Top
    $nw = [int]($fallback.Right - $fallback.Left)
    $nh = [int]($fallback.Bottom - $fallback.Top)
  }
  $ok = $true
  if ($showCmd -eq 2) {
    $ok = [SnipWin]::Minimize($hwnd)
  } elseif ($showCmd -eq 3) {
    if ([SnipWin]::ShowCmdOf($hwnd) -ne 3) { $ok = [SnipWin]::Maximize($hwnd) }
  } else {
    $now = [SnipWin]::WindowRect($hwnd)
    $drifted = ([SnipWin]::ShowCmdOf($hwnd) -ne 1) -or
      ([Math]::Abs($now.Left - $nl) -gt 2) -or ([Math]::Abs($now.Top - $nt) -gt 2) -or
      ([Math]::Abs(($now.Right - $now.Left) - $nw) -gt 2) -or ([Math]::Abs(($now.Bottom - $now.Top) - $nh) -gt 2)
    if ($drifted) {
      # SW_RESTORE both un-maximizes and shows a window the app had hidden.
      [void][SnipWin]::Show($hwnd, 9)
      Start-Sleep -Milliseconds 160
      $ok = [SnipWin]::Place($hwnd, $nl, $nt, $nw, $nh)
    }
    # Some applications keep their own visibility state and hide the window
    # again right after an outside move; show it once more without moving it.
    if (-not [SnipWin]::Visible($hwnd)) {
      [void][SnipWin]::Show($hwnd, 9)
      Start-Sleep -Milliseconds 150
      $ok = [SnipWin]::Place($hwnd, $nl, $nt, $nw, $nh)
    }
  }
  if ($saved.topmost) { [void][SnipWin]::SetTopmost($hwnd, $false) }
  $now = [SnipWin]::Placement($hwnd)
  $visible = [SnipWin]::Visible($hwnd)
  return [pscustomobject]@{
    ok = ([bool]$ok -and $visible)
    visible = $visible
    showCmd = [int]$now.showCmd
    normal = (To-Rect $now.rcNormalPosition.Left $now.rcNormalPosition.Top $now.rcNormalPosition.Right $now.rcNormalPosition.Bottom)
  }
}

function Invoke-Arrange {
  $wins = @(Select-Wins @([SnipWin]::List()))
  if ($wins.Count -eq 0) {
    if ($env:SNIP_HWND) { throw ('The window ' + $env:SNIP_HWND + ' is no longer visible.') }
    $cands = @(@([SnipWin]::List()) | Where-Object { $_.title } | Select-Object -First 10)
    $hint = ''
    if ($cands.Count -gt 0) {
      $hint = ' Visible windows: ' + ((@($cands | ForEach-Object { $_.app + ' | ' + $_.title })) -join '; ')
    }
    throw ('No visible window matched app="' + $env:SNIP_APP + '" title="' + $env:SNIP_TITLE + '" pid="' + $env:SNIP_PID + '".' + $hint)
  }
  $target = $wins | Sort-Object -Property @{ Expression = { if ($_.foreground) { 1 } else { 0 } }; Descending = $true }, @{ Expression = { [long]$_.width * [long]$_.height }; Descending = $true } | Select-Object -First 1
  $hwnd = [IntPtr][long]$target.hwnd
  $before = [SnipWin]::Placement($hwnd)
  $savedBefore = [pscustomobject]@{
    flags = [int]$before.flags
    showCmd = [int]$before.showCmd
    minX = [int]$before.ptMinPosition.X
    minY = [int]$before.ptMinPosition.Y
    maxX = [int]$before.ptMaxPosition.X
    maxY = [int]$before.ptMaxPosition.Y
    normal = (To-Rect $before.rcNormalPosition.Left $before.rcNormalPosition.Top $before.rcNormalPosition.Right $before.rcNormalPosition.Bottom)
  }
  $changed = $false

  if ($before.showCmd -eq 2) {
    [void][SnipWin]::Restore($hwnd)
    $changed = $true
    Start-Sleep -Milliseconds 180
  }
  $mode = $env:SNIP_MODE
  if ($mode -eq 'maximize') {
    if ([SnipWin]::ShowCmdOf($hwnd) -ne 3) {
      [void][SnipWin]::Maximize($hwnd)
      $changed = $true
    }
  }
  [void][SnipWin]::Activate($hwnd)
  $raised = $false
  if (-not [SnipWin]::IsTopmost($hwnd)) {
    [void][SnipWin]::SetTopmost($hwnd, $true)
    $raised = $true
    $savedBefore | Add-Member -NotePropertyName topmost -NotePropertyValue $true
  } else {
    $savedBefore | Add-Member -NotePropertyName topmost -NotePropertyValue $false
  }

  $settle = 500
  if ($env:SNIP_SETTLE) { $settle = [int]$env:SNIP_SETTLE }
  if ($settle -gt 0) { Start-Sleep -Milliseconds $settle }

  $frame = [SnipWin]::VisibleFrame($hwnd)
  $work = [SnipWin]::WorkAreaOf($hwnd)
  $maximized = ([SnipWin]::ShowCmdOf($hwnd) -eq 3)

  $capture = $null
  if ($env:SNIP_AREA) {
    $asked = $env:SNIP_AREA | ConvertFrom-Json
    $al = [int]$asked.left
    $at = [int]$asked.top
    $aw = [int]$asked.width
    $ah = [int]$asked.height
    if ($aw -le 0 -or $ah -le 0) { throw 'area width and height must be positive' }
    if (($al -lt $frame.Left) -or ($at -lt $frame.Top) -or (($al + $aw) -gt $frame.Right) -or (($at + $ah) -gt $frame.Bottom)) {
      throw ('Refused: the requested area ' + $aw + 'x' + $ah + ' at ' + $al + ',' + $at + ' is not fully inside the ' + $target.app + ' window, which occupies ' + ($frame.Right - $frame.Left) + 'x' + ($frame.Bottom - $frame.Top) + ' at ' + $frame.Left + ',' + $frame.Top + '.')
    }
    $capture = [pscustomobject]@{ left = $al; top = $at; width = $aw; height = $ah }
  } else {
    $left = [Math]::Max($frame.Left, $work.Left)
    $top = [Math]::Max($frame.Top, $work.Top)
    $right = [Math]::Min($frame.Right, $work.Right)
    $bottom = [Math]::Min($frame.Bottom, $work.Bottom)
    # A window that is not maximized has rounded corners on Windows 11; the
    # corner pixels show whatever is behind it, so keep mode trims them.
    $inset = 0
    if (-not $maximized) { $inset = 8 }
    $left = $left + $inset
    $top = $top + $inset
    $right = $right - $inset
    $bottom = $bottom - $inset
    if (($right - $left) -le 0 -or ($bottom - $top) -le 0) { throw 'The target window has no visible area to capture.' }
    $capture = [pscustomobject]@{ left = $left; top = $top; width = ($right - $left); height = ($bottom - $top) }
  }

  $cover = Test-Coverage ([long]$target.hwnd) ([int]$target.pid) $capture
  $trimmed = $false
  $original = $null
  $trimReason = ''
  if (-not $cover.ok -and -not $env:SNIP_AREA) {
    $clean = Get-CleanRect $capture $cover.obstacles
    if ($clean) {
      $confirm = Test-Coverage ([long]$target.hwnd) ([int]$target.pid) $clean
      if ($confirm.ok) {
        $original = $capture
        $capture = $clean
        $trimReason = $cover.offender
        $cover = $confirm
        $trimmed = $true
      }
    }
  }
  if (-not $cover.ok) {
    if ($changed -or $raised) {
      [void](Set-SavedPlacement $hwnd $savedBefore)
    }
    throw ('Refused: the ' + $target.app + ' window is not fully visible; ' + $cover.offender + ' overlaps it at ' + $cover.bad + ' of ' + $cover.samples + ' sample points, and no large enough clean rectangle is left. Nothing was captured. Close or move the overlapping window, activate the target window, or use snip_view.')
  }

  return [pscustomobject]@{
    ok = $true
    hwnd = [long]$target.hwnd
    pid = [int]$target.pid
    app = $target.app
    title = $target.title
    window = (To-Rect $frame.Left $frame.Top $frame.Right $frame.Bottom)
    capture = $capture
    maximized = $maximized
    changed = $changed
    samples = $cover.samples
    trimmed = $trimmed
    trimmedBy = $trimReason
    original = $original
    placement = $savedBefore
  }
}

function Invoke-Verify {
  $hwnd = [IntPtr][long]$env:SNIP_HWND
  $procId = [int]$env:SNIP_PID
  $rect = $env:SNIP_AREA | ConvertFrom-Json
  $cover = Test-Coverage ([long]$env:SNIP_HWND) $procId $rect
  $restore = $null
  if (($env:SNIP_RESTORE -eq '1') -and $env:SNIP_PLACEMENT) {
    $saved = $env:SNIP_PLACEMENT | ConvertFrom-Json
    $restore = Set-SavedPlacement $hwnd $saved
  } elseif ($env:SNIP_PLACEMENT) {
    # Even when the caller keeps the arranged geometry, the temporary topmost
    # flag must go: the user never asked for a permanently raised window.
    $saved = $env:SNIP_PLACEMENT | ConvertFrom-Json
    if ($saved.topmost) { [void][SnipWin]::SetTopmost($hwnd, $false) }
  }
  return [pscustomobject]@{
    ok = $cover.ok
    samples = $cover.samples
    bad = $cover.bad
    offender = $cover.offender
    restored = ($restore -ne $null -and $restore.ok)
    window = $restore
  }
}

# Pure computation on a window that is already in place: report whether the
# rectangle is still clean, and if not, the largest verified sub-rectangle that
# is. It never moves, shows, or activates the window, so a retry keeps the
# arrangement (and the temporary topmost flag) the first attempt relied on.
function Invoke-Trim {
  $rect = $env:SNIP_AREA | ConvertFrom-Json
  $cover = Test-Coverage ([long]$env:SNIP_HWND) ([int]$env:SNIP_PID) $rect
  if ($cover.ok) {
    return [pscustomobject]@{
      ok = $true
      trimmed = $false
      capture = $rect
      samples = $cover.samples
      offender = ''
    }
  }
  $clean = Get-CleanRect $rect $cover.obstacles
  if ($clean) {
    $confirm = Test-Coverage ([long]$env:SNIP_HWND) ([int]$env:SNIP_PID) $clean
    if ($confirm.ok) {
      return [pscustomobject]@{
        ok = $true
        trimmed = $true
        capture = $clean
        original = $rect
        samples = $confirm.samples
        offender = $cover.offender
      }
    }
  }
  return [pscustomobject]@{
    ok = $false
    trimmed = $false
    samples = $cover.samples
    bad = $cover.bad
    offender = $cover.offender
  }
}

function Invoke-WorkArea {
  $r = [SnipWin]::PrimaryWorkArea()
  return (To-Rect $r.Left $r.Top $r.Right $r.Bottom)
}

# Chromium browsers may hand a launch off to a fresh process, so the pid that
# was spawned is not necessarily the one that owns the window. The temporary
# profile directory is unique to one viewer instance and survives the hand-off
# on every process of that instance, which makes it the reliable identity.
function Get-MarkedProcesses([string]$name, [string]$marker) {
  $needle = $marker.ToLowerInvariant()
  $items = @()
  try {
    if ($name) {
      $items = @(Get-CimInstance Win32_Process -Filter ("Name='" + $name + "'") -ErrorAction Stop)
    } else {
      $items = @(Get-CimInstance Win32_Process -ErrorAction Stop)
    }
  } catch {
    if ($name) {
      $items = @(Get-WmiObject Win32_Process -Filter ("Name='" + $name + "'") -ErrorAction Stop)
    } else {
      $items = @(Get-WmiObject Win32_Process -ErrorAction Stop)
    }
  }
  $pids = New-Object System.Collections.ArrayList
  foreach ($p in $items) {
    $cmd = $p.CommandLine
    if (-not $cmd) { continue }
    if ($cmd.ToLowerInvariant().Contains($needle)) { [void]$pids.Add([int]$p.ProcessId) }
  }
  return @($pids)
}

function Invoke-Owner {
  $marker = $env:SNIP_MARKER
  if (-not $marker) { throw 'owner requires SNIP_MARKER' }
  $pids = Get-MarkedProcesses $env:SNIP_PROCESS $marker
  $set = @{}
  foreach ($p in $pids) { $set[[int]$p] = 1 }
  $wins = @(@([SnipWin]::List()) | Where-Object { $set.ContainsKey([int]$_.pid) })
  return [pscustomobject]@{ pids = $pids; windows = $wins }
}

function Invoke-Foreground {
  $hwnd = [SnipWin]::ForegroundHwnd()
  if ($hwnd -eq [IntPtr]::Zero) { $hwnd = [SnipWin]::TopWindow() }
  if ($hwnd -eq [IntPtr]::Zero) {
    return [pscustomobject]@{ found = $false; app = ''; title = ''; pid = 0 }
  }
  $root = [SnipWin]::RootOf($hwnd)
  $procId = [SnipWin]::PidOf($root)
  $app = ''
  try { $app = (Get-Process -Id $procId -ErrorAction Stop).ProcessName } catch { }
  $r = [SnipWin]::WindowRect($root)
  return [pscustomobject]@{
    found = $true
    app = $app
    title = [SnipWin]::TitleOf($root)
    pid = $procId
    window = (To-Rect $r.Left $r.Top $r.Right $r.Bottom)
  }
}

try {
  $result = $null
  switch ($env:SNIP_CMD) {
    'list' { $result = Invoke-List }
    'arrange' { $result = Invoke-Arrange }
    'verify' { $result = Invoke-Verify }
    'trim' { $result = Invoke-Trim }
    'workarea' { $result = Invoke-WorkArea }
    'foreground' { $result = Invoke-Foreground }
    'owner' { $result = Invoke-Owner }
    default { throw ('Unknown window command: ' + $env:SNIP_CMD) }
  }
  $result | ConvertTo-Json -Depth 8 -Compress
} catch {
  [pscustomobject]@{ error = $_.Exception.Message } | ConvertTo-Json -Depth 4 -Compress
}
`;

let scriptPromise = null;

async function scriptPath() {
  if (!scriptPromise) {
    scriptPromise = (async () => {
      const dir = join(tmpdir(), 'snipaste-mcp');
      await mkdir(dir, { recursive: true });
      const stamp = createHash('sha1').update(PS_SCRIPT).digest('hex').slice(0, 10);
      const file = join(dir, `win32-${stamp}.ps1`);
      await writeFile(file, PS_SCRIPT, 'utf8');
      return file;
    })();
  }
  return scriptPromise;
}

async function run(command, vars, timeout = 30000) {
  if (!WINDOW_CONTROL) {
    throw new Error('Window control is Windows-only in this build.');
  }
  const file = await scriptPath();
  const env = { ...process.env, SNIP_CMD: command };
  for (const [key, value] of Object.entries(vars)) {
    env[key] = value === undefined || value === null ? '' : String(value);
  }
  const { stdout } = await execFileAsync(
    'powershell',
    ['-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', file],
    { windowsHide: true, timeout, maxBuffer: 8 * 1024 * 1024, encoding: 'utf8', env },
  );
  const text = stdout.replace(/^\uFEFF/, '').trim();
  if (!text) return null;
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error(`Window control returned unexpected output: ${text.slice(0, 400)}`);
  }
  if (parsed && parsed.error) throw new Error(parsed.error);
  return parsed;
}

const asArray = (value) => (Array.isArray(value) ? value : value ? [value] : []);

export async function listWindows({ app, title, pid, limit = 20 } = {}) {
  const result = await run('list', { SNIP_APP: app, SNIP_TITLE: title, SNIP_PID: pid, SNIP_LIMIT: limit });
  return { total: result.total ?? 0, windows: asArray(result.windows) };
}

export async function arrangeAndVerify({ app, title, pid, hwnd, mode = 'maximize', settleMs = 500, area } = {}) {
  return run('arrange', {
    SNIP_APP: app,
    SNIP_TITLE: title,
    SNIP_PID: pid,
    SNIP_HWND: hwnd,
    SNIP_MODE: mode,
    SNIP_SETTLE: settleMs,
    SNIP_AREA: area ? JSON.stringify(area) : undefined,
  });
}

export async function verifyAndRestore({ hwnd, pid, capture, placement, restore = true }) {
  return run('verify', {
    SNIP_HWND: hwnd,
    SNIP_PID: pid,
    SNIP_AREA: JSON.stringify(capture),
    SNIP_PLACEMENT: placement ? JSON.stringify(placement) : undefined,
    SNIP_RESTORE: restore ? '1' : '0',
  });
}

// Re-verifies a rectangle on a window that is already in place and returns the
// largest verified sub-rectangle when something covers part of it. Nothing is
// moved or activated, so the arrangement survives.
export async function trimRect({ hwnd, pid, capture }) {
  return run('trim', {
    SNIP_HWND: hwnd,
    SNIP_PID: pid,
    SNIP_AREA: JSON.stringify(capture),
  });
}

export async function workArea() {
  return run('workarea', {});
}

export async function foregroundWindow() {
  return run('foreground', {});
}

export async function processWindows({ marker, image } = {}) {
  const result = await run('owner', { SNIP_MARKER: marker, SNIP_PROCESS: image });
  return { pids: asArray(result.pids).map(Number), windows: asArray(result.windows) };
}
