param([string]$Out = "shot.png", [int]$ProcId = 0, [string]$ClassFilter = "SkinWindowClass", [int]$Pad = 0, [switch]$MainOnly)
# Cattura (PrintWindow) tutte le finestre della skin di un processo vlc (o di tutti) e le compone su una tela.
# Stampa anche il DPI con cui Windows tratta ogni finestra (96 = non consapevole/virtualizzata, 144 = 150% reale).
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class W3 {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr ctx);
  [DllImport("user32.dll")] public static extern uint GetDpiForWindow(IntPtr h);
}
"@
[W3]::SetProcessDpiAwarenessContext([IntPtr](-4)) | Out-Null
if ($ProcId -ne 0) { $pids = @([uint32]$ProcId) } else { $pids = @((Get-Process vlc -ErrorAction SilentlyContinue) | ForEach-Object { [uint32]$_.Id }) }
if ($pids.Count -eq 0) { Write-Output "NO_VLC"; exit 1 }
$script:wins = @()
$cb = [W3+EnumProc]{ param($h, $l)
    $p = [uint32]0; [W3]::GetWindowThreadProcessId($h, [ref]$p) | Out-Null
    if (($pids -contains $p) -and [W3]::IsWindowVisible($h)) {
        $sb = New-Object System.Text.StringBuilder 256
        [W3]::GetClassName($h, $sb, 256) | Out-Null
        if ($sb.ToString() -eq $ClassFilter) {
            $r = New-Object W3+RECT
            [W3]::GetWindowRect($h, [ref]$r) | Out-Null
            $w = [int]($r.R - $r.L); $hh = [int]($r.B - $r.T)
            $dpi = [W3]::GetDpiForWindow($h)
            if ($w -gt 50 -and $hh -gt 50) { $script:wins += ,@($h, [int]$r.L, [int]$r.T, $w, $hh, [int]$dpi) }
        }
    }
    return $true }
[W3]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
if ($script:wins.Count -eq 0) { Write-Output "NO_WINDOW"; exit 2 }
if ($MainOnly) { $big = $script:wins | Sort-Object { $_[3] * $_[4] } -Descending | Select-Object -First 1; $script:wins = @(,$big) }
foreach ($wi in $script:wins) { Write-Output ("WIN " + $wi[1] + "," + $wi[2] + " " + $wi[3] + "x" + $wi[4] + " dpi=" + $wi[5]) }
$L = [int]([Linq.Enumerable]::Min([int[]]($script:wins | ForEach-Object { $_[1] }))) - $Pad
$T = [int]([Linq.Enumerable]::Min([int[]]($script:wins | ForEach-Object { $_[2] }))) - $Pad
$R = [int]([Linq.Enumerable]::Max([int[]]($script:wins | ForEach-Object { $_[1] + $_[3] }))) + $Pad
$B = [int]([Linq.Enumerable]::Max([int[]]($script:wins | ForEach-Object { $_[2] + $_[4] }))) + $Pad
$W = [int]($R - $L); $H = [int]($B - $T)
$canvas = New-Object System.Drawing.Bitmap -ArgumentList $W, $H
$g = [System.Drawing.Graphics]::FromImage($canvas)
$g.Clear([System.Drawing.Color]::FromArgb(255, 70, 74, 84))
[array]::Reverse($script:wins)
foreach ($wi in $script:wins) {
    $bmp = New-Object System.Drawing.Bitmap -ArgumentList $wi[3], $wi[4]
    $gw = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $gw.GetHdc()
    $ok = [W3]::PrintWindow($wi[0], $hdc, 2)
    $gw.ReleaseHdc($hdc)
    $g.DrawImage($bmp, ($wi[1] - $L), ($wi[2] - $T))
}
$canvas.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
Write-Output ("SAVED " + $Out + " " + $W + "x" + $H + " windows=" + $script:wins.Count + " origin=" + $L + "," + $T)
