param([int]$ProcId, [int]$X, [int]$Y, [int]$W = 0, [int]$H = 0, [switch]$Click, [int]$Settle = 700)
# Porta il puntatore (e opzionalmente clicca) nel punto (X,Y) relativo a una finestra della skin
# dell'istanza di PROVA indicata da ProcId. La finestra e' scelta per dimensione WxH (0 = la piu' grande).
# Coordinate 1:1 in pixel fisici: il processo VLC e' consapevole dei DPI, nessun fattore di scala.
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class W5 {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr ctx);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
}
"@
[W5]::SetProcessDpiAwarenessContext([IntPtr](-4)) | Out-Null
$script:rows = @()
$cb = [W5+EnumProc]{ param($h, $l)
    $p = [uint32]0; [W5]::GetWindowThreadProcessId($h, [ref]$p) | Out-Null
    if ($p -eq [uint32]$ProcId -and [W5]::IsWindowVisible($h)) {
        $sb = New-Object System.Text.StringBuilder 256; [W5]::GetClassName($h, $sb, 256) | Out-Null
        if ($sb.ToString() -eq "SkinWindowClass") {
            $r = New-Object W5+RECT; [W5]::GetWindowRect($h, [ref]$r) | Out-Null
            $script:rows += [PSCustomObject]@{ H = $h; L = [int]$r.L; T = [int]$r.T; W = [int]($r.R - $r.L); Hh = [int]($r.B - $r.T) }
        }
    }
    return $true }
[W5]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
if ($W -gt 0) { $win = $script:rows | Where-Object { $_.W -eq $W -and $_.Hh -eq $H } | Select-Object -First 1 }
else { $win = $script:rows | Sort-Object { $_.W * $_.Hh } -Descending | Select-Object -First 1 }
if (-not $win) { Write-Output "NO_WINDOW"; exit 2 }
[W5]::SetForegroundWindow($win.H) | Out-Null
Start-Sleep -Milliseconds 350
$px = $win.L + $X; $py = $win.T + $Y
[W5]::SetCursorPos($px, $py) | Out-Null
Start-Sleep -Milliseconds 150
[W5]::SetCursorPos($px + 1, $py) | Out-Null
Start-Sleep -Milliseconds 150
[W5]::SetCursorPos($px, $py) | Out-Null
if ($Click) {
    Start-Sleep -Milliseconds 200
    [W5]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 90; [W5]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
}
Start-Sleep -Milliseconds $Settle
Write-Output ("POINTER " + $px + "," + $py + " win=" + $win.W + "x" + $win.Hh + " click=" + $Click)
