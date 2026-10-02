--[[
 youtube.lua per VLC 3.x su Windows: risolve i link YouTube tramite yt-dlp.
 Installato in %APPDATA%/vlc/lua/playlist/youtube.lua (ha priorita' su quello di sistema).
 Ispirato a https://github.com/vulpinerey/vlc-youtube-lua (versione Linux), riscritto per Windows.

 Requisiti: yt-dlp.exe in %LOCALAPPDATA%/Programs/yt-dlp, oppure installato con winget
 (yt-dlp.yt-dlp, ambito utente o macchina), oppure nel PATH, oppure percorso indicato nella variabile d'ambiente YTDLP_BIN.
 Formato opzionale nella variabile d'ambiente YTDLP_FORMAT
 (predefinito: bestvideo[height<=1080]+bestaudio/best).

 Nota: il sorgente evita volutamente il carattere backslash; i percorsi usano "/" e vengono
 convertiti con to_win() prima di essere passati a cmd.exe.
--]]

local BS = string.char(92) -- backslash

local function to_win(path)
    return (path:gsub("/", BS))
end

local function file_exists(path)
    local f = io.open(path, "rb")
    if f then f:close() return true end
    return false
end

local function pick_yt_dlp()
    local env_bin = os.getenv("YTDLP_BIN")
    if env_bin and env_bin ~= "" then return env_bin end
    local localapp = (os.getenv("LOCALAPPDATA") or ""):gsub(BS, "/")
    local progfiles = (os.getenv("ProgramFiles") or "C:/Program Files"):gsub(BS, "/")
    local candidates = {
        localapp .. "/Programs/yt-dlp/yt-dlp.exe",
        localapp .. "/Microsoft/WinGet/Links/yt-dlp.exe",
        progfiles .. "/WinGet/Links/yt-dlp.exe",
        "C:/Program Files/yt-dlp/yt-dlp.exe",
        "C:/yt-dlp/yt-dlp.exe",
    }
    for _, c in ipairs(candidates) do
        local ok = file_exists(c)
        vlc.msg.dbg("[youtube.lua/yt-dlp] candidato " .. c .. " -> " .. tostring(ok))
        if ok then return to_win(c) end
    end
    return "yt-dlp.exe" -- affidati al PATH del processo VLC
end

function probe()
    if not (vlc.access == "http" or vlc.access == "https") then
        return false
    end
    local p = vlc.path
    local host_ok = p:match("^www%.youtube%.com/") or p:match("^youtube%.com/")
        or p:match("^m%.youtube%.com/") or p:match("^music%.youtube%.com/")
        or p:match("^youtu%.be/")
    if not host_ok then return false end
    return (p:match("/watch%?") or p:match("/shorts/") or p:match("/embed/")
        or p:match("/live/") or p:match("^youtu%.be/[%w%-_]+")) and true or false
end

local function run_yt_dlp(binary, url, fmt)
    -- Doppia coppia di virgolette esterne: cmd.exe /c toglie la prima e l'ultima,
    -- cosi' il percorso dell'eseguibile puo' contenere spazi.
    local cmd = string.format(
        '""%s" --no-playlist --no-warnings --encoding utf-8 -f "%s" --print title --print urls -- "%s""',
        binary, fmt, url)
    vlc.msg.dbg("[youtube.lua/yt-dlp] cmd: " .. cmd)
    local p = io.popen(cmd, "r")
    if not p then return nil end
    local lines = {}
    for line in p:lines() do
        line = line:gsub("^%s+", ""):gsub("%s+$", "")
        if line ~= "" then table.insert(lines, line) end
    end
    p:close()
    return lines
end

function parse()
    local url = vlc.access .. "://" .. vlc.path
    -- Accetta solo caratteri sicuri per la riga di comando di cmd.exe
    if not url:match("^[%w%-%._~:/?#@!$&'()*+,;=]+$") then
        vlc.msg.err("[youtube.lua/yt-dlp] URL con caratteri non ammessi: " .. url)
        return {}
    end
    local binary = pick_yt_dlp()
    local fmt = os.getenv("YTDLP_FORMAT")
    if not fmt or fmt == "" then fmt = "bestvideo[height<=1080]+bestaudio/best" end
    vlc.msg.dbg("[youtube.lua/yt-dlp] binario: " .. binary)

    local lines = run_yt_dlp(binary, url, fmt)
    if not lines or #lines < 2 then
        lines = run_yt_dlp(binary, url, "best")
    end
    if not lines or #lines < 2 then
        vlc.msg.err("[youtube.lua/yt-dlp] nessun URL ottenuto per " .. url ..
            " - controlla che yt-dlp.exe sia installato e raggiungibile (PATH o YTDLP_BIN)")
        return {}
    end

    local title = lines[1]
    local video_url = lines[2]
    local audio_url = lines[3]
    local item = { path = video_url, name = title, url = url }
    if audio_url and audio_url ~= video_url then
        item.options = { ":input-slave=" .. audio_url }
    end
    return { item }
end
