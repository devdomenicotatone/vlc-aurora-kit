param([int]$X = 28, [int]$Y = 24, [string]$Out = "")
# Clicca nel punto (X,Y) relativo alla finestra principale della skin (la piu' grande SkinWindowClass) e opzionalmente cattura lo schermo attorno alla finestra.
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class W4 {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr ctx);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
  [DllImport("user32.dll")] public static extern IntPtr MonitorFromWindow(IntPtr h, uint flags);
  [DllImport("shcore.dll")] public static extern int GetDpiForMonitor(IntPtr mon, int type, out uint dx, out uint dy);
}
"@
[W4]::SetProcessDpiAwarenessContext([IntPtr](-4)) | Out-Null
$pids = @((Get-Process vlc -ErrorAction SilentlyContinue) | ForEach-Object { [uint32]$_.Id })
if ($pids.Count -eq 0) { Write-Output "NO_VLC"; exit 1 }
$script:best = $null
$cb = [W4+EnumProc]{ param($h, $l)
    $p = [uint32]0; [W4]::GetWindowThreadProcessId($h, [ref]$p) | Out-Null
    if (($pids -contains $p) -and [W4]::IsWindowVisible($h)) {
        $sb = New-Object System.Text.StringBuilder 256
        [W4]::GetClassName($h, $sb, 256) | Out-Null
        if ($sb.ToString() -eq "SkinWindowClass") {
            $r = New-Object W4+RECT
            [W4]::GetWindowRect($h, [ref]$r) | Out-Null
            $w = [int]($r.R - $r.L); $hh = [int]($r.B - $r.T)
            Write-Output ("WIN " + $r.L + "," + $r.T + " " + $w + "x" + $hh)
            if ($w -ge 900 -and $hh -ge 500) { $script:best = @($h, [int]$r.L, [int]$r.T, $w, $hh) }
        }
    }
    return $true }
[W4]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
if (-not $script:best) { Write-Output "NO_MAIN"; exit 2 }
$h = $script:best[0]; $L = $script:best[1]; $T = $script:best[2]; $Wd = $script:best[3]; $Ht = $script:best[4]
# VLC skins2 non e' DPI-aware: le coordinate logiche della skin vanno moltiplicate per la scala del monitor
$mon = [W4]::MonitorFromWindow($h, 2)
$dx = [uint32]96; $dy = [uint32]96
[W4]::GetDpiForMonitor($mon, 0, [ref]$dx, [ref]$dy) | Out-Null
$scale = $dx / 96.0
Write-Output ("SCALE " + $scale)
$X = [int]($X * $scale); $Y = [int]($Y * $scale)
[W4]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 500
[W4]::SetCursorPos($L + $X, $T + $Y) | Out-Null
Start-Sleep -Milliseconds 250
[W4]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 120
[W4]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 900
Write-Output ("CLICKED " + ($L + $X) + "," + ($T + $Y))
if ($Out -ne "") {
    $pad = 300
    $bmp = New-Object System.Drawing.Bitmap -ArgumentList ($Wd + 2 * $pad), ($Ht + 2 * $pad)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($L - $pad, $T - $pad, 0, 0, (New-Object System.Drawing.Size -ArgumentList ($Wd + 2 * $pad), ($Ht + 2 * $pad)))
    $bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output ("SAVED " + $Out)
}
