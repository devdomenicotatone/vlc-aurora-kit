param([string]$Out = "shot.png", [string]$ClassFilter = "SkinWindowClass", [int]$Pad = 0)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices;
public class W2 {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr ctx);
}
"@
if (-not [W2]::SetProcessDpiAwarenessContext([IntPtr](-4))) { [W2]::SetProcessDPIAware() | Out-Null }
$procs = Get-Process vlc -ErrorAction SilentlyContinue
if (-not $procs) { Write-Output "NO_VLC"; exit 1 }
$pids = @($procs | ForEach-Object { [uint32]$_.Id })
$script:wins = @()
$cb = [W2+EnumProc]{ param($h, $l)
    $p = [uint32]0; [W2]::GetWindowThreadProcessId($h, [ref]$p) | Out-Null
    if (($pids -contains $p) -and [W2]::IsWindowVisible($h)) {
        $sb = New-Object System.Text.StringBuilder 256
        [W2]::GetClassName($h, $sb, 256) | Out-Null
        if ($sb.ToString() -eq $ClassFilter) {
            $r = New-Object W2+RECT
            [W2]::GetWindowRect($h, [ref]$r) | Out-Null
            $w = [int]($r.R - $r.L); $hh = [int]($r.B - $r.T)
            Write-Output ("WIN " + $r.L + "," + $r.T + " " + $w + "x" + $hh)
            if ($w -gt 50 -and $hh -gt 50) { $script:wins += ,@($h, [int]$r.L, [int]$r.T, $w, $hh) }
        }
    }
    return $true }
[W2]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
if ($script:wins.Count -eq 0) { Write-Output "NO_WINDOW"; exit 2 }
# tela che contiene tutte le finestre skin
$L = [int]([Linq.Enumerable]::Min([int[]]($script:wins | ForEach-Object { $_[1] }))) - $Pad
$T = [int]([Linq.Enumerable]::Min([int[]]($script:wins | ForEach-Object { $_[2] }))) - $Pad
$R = [int]([Linq.Enumerable]::Max([int[]]($script:wins | ForEach-Object { $_[1] + $_[3] }))) + $Pad
$B = [int]([Linq.Enumerable]::Max([int[]]($script:wins | ForEach-Object { $_[2] + $_[4] }))) + $Pad
$W = [int]($R - $L); $H = [int]($B - $T)
$canvas = New-Object System.Drawing.Bitmap -ArgumentList $W, $H
$g = [System.Drawing.Graphics]::FromImage($canvas)
$g.Clear([System.Drawing.Color]::FromArgb(255, 70, 74, 84))
[array]::Reverse($script:wins)   # EnumWindows restituisce dall'alto verso il basso: disegna prima quelle sotto
foreach ($w in $script:wins) {
    $bmp = New-Object System.Drawing.Bitmap -ArgumentList $w[3], $w[4]
    $gw = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $gw.GetHdc()
    $ok = [W2]::PrintWindow($w[0], $hdc, 2)   # PW_RENDERFULLCONTENT
    $gw.ReleaseHdc($hdc)
    Write-Output ("PRINT ok=" + $ok)
    $g.DrawImage($bmp, ($w[1] - $L), ($w[2] - $T))
}
$canvas.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
Write-Output ("SAVED " + $Out + " " + $W + "x" + $H + " windows=" + $script:wins.Count)
