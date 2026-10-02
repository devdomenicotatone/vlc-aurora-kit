# -*- coding: utf-8 -*-
"""Applica la patch "Snap nativo di Windows" ai sorgenti di skins2 (VLC 3.0.24).
Copia modules/gui/skins2 in skins2-patched/ e modifica i file; i sorgenti originali restano intatti.
La cartella di lavoro (quella che contiene src/vlc-3.0.24) e' la cartella dello script oppure,
se impostata, la variabile d'ambiente SKINS2_BUILD."""
import os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("SKINS2_BUILD") or HERE
ORIG = os.path.join(WORK, "src", "vlc-3.0.24", "modules", "gui", "skins2")
DST = os.path.join(WORK, "skins2-patched")
if os.path.isdir(DST):
    shutil.rmtree(DST)
shutil.copytree(ORIG, DST)


MODIFICATI = set()   # file toccati: alla fine ricevono la nota richiesta dalla GPL


def patch(rel, pairs):
    MODIFICATI.add(rel)
    p = os.path.join(DST, rel)
    s = open(p, encoding="utf-8", newline="").read()
    for old, new in pairs:
        if s.count(old) != 1:
            sys.exit("ANCORA NON TROVATA (%d) in %s:\n%s" % (s.count(old), rel, old[:120]))
        s = s.replace(old, new)
    open(p, "w", encoding="utf-8", newline="").write(s)
    print("patch", rel)


def patch_between(rel, start, end, new):
    """Sostituisce il blocco che va da start a end (compresi), per riscrivere una funzione intera."""
    MODIFICATI.add(rel)
    p = os.path.join(DST, rel)
    s = open(p, encoding="utf-8", newline="").read()
    if s.count(start) != 1:
        sys.exit("INIZIO NON TROVATO (%d) in %s:\n%s" % (s.count(start), rel, start[:120]))
    i = s.index(start)
    j = s.find(end, i + len(start))
    if j < 0:
        sys.exit("FINE NON TROVATA in %s:\n%s" % (rel, end[:120]))
    s = s[:i] + new + s[j + len(end):]
    open(p, "w", encoding="utf-8", newline="").write(s)
    print("patch", rel)


# ------------------------------------------------------------------ interfaccia OSWindow
patch("src/os_window.hpp", [(
"""    /// updateWindow (tell the OS we need to update the window)
    virtual bool invalidateRect( int x, int y, int w, int h ) const = 0;

protected:""",
"""    /// updateWindow (tell the OS we need to update the window)
    virtual bool invalidateRect( int x, int y, int w, int h ) const = 0;

    /// Snap support: true when the window carries a system sizing frame so
    /// that the OS can arrange it (Windows Snap, Win+arrows, snap layouts)
    virtual bool isSnappable() const { return false; }

    /// Let the system drive a drag of the window; returns when the drag is
    /// over, or false at once if the platform does not support it
    virtual bool startNativeMove() const { return false; }

    /// Ask the system to maximize or restore the window; false if unsupported
    virtual bool setMaximized( bool maximized ) const
        { (void)maximized; return false; }

    /// True while the plugin itself is moving/resizing the OS window, so the
    /// loop can ignore the resulting system notifications (avoids a feedback
    /// loop between moveResize() and onOSGeometryChange())
    virtual bool isSelfMoving() const { return false; }

protected:""")])

# ------------------------------------------------------------------ Win32Window
patch("win32/win32_window.hpp", [(
"""    /// invalidate a window surface
    bool invalidateRect( int x, int y, int w, int h ) const;
""",
"""    /// invalidate a window surface
    bool invalidateRect( int x, int y, int w, int h ) const;

    /// Snap support (top-level skin windows only)
    virtual bool isSnappable() const { return m_snappable; }

    /// System driven drag (SC_MOVE loop): Windows Snap, snap layouts, shake...
    virtual bool startNativeMove() const;

    /// System maximize / restore
    virtual bool setMaximized( bool maximized ) const;

    /// See OSWindow::isSelfMoving
    virtual bool isSelfMoving() const { return m_selfMove > 0; }

    /// Shape of a snappable window. A rectangular one (systemFrame) is left
    /// without region, so that the DWM renders its frame: shadow and, on
    /// Windows 11, rounded corners and a border in the given colour. A
    /// shaped one keeps the region that the caller applies.
    void setSystemFrame( bool systemFrame, COLORREF border ) const;
"""), (
"""    /// window type
    GenericWindow::WindowType_t m_type;
""",
"""    /// window type
    GenericWindow::WindowType_t m_type;
    /// true for top-level skin windows (system sizing frame, snappable)
    bool m_snappable;
    /// >0 while moveResize() drives the window (guards the OS-geometry sync)
    mutable int m_selfMove;
    /// true while a region is applied to the window (shaped skin)
    mutable bool m_hasRegion;
    /// border colour last given to the DWM (CLR_INVALID: none yet)
    mutable COLORREF m_borderColor;
""")])

patch("win32/win32_window.cpp", [(
"""#include "win32_factory.hpp"


/// Fading API""",
"""#include "win32_factory.hpp"
#include <dwmapi.h>


// Window attributes of the DWM: the Windows 11 ones are missing from older
// SDK headers, and older systems just refuse them
#define SKINS_DWMWA_USE_IMMERSIVE_DARK_MODE_OLD  19
#define SKINS_DWMWA_USE_IMMERSIVE_DARK_MODE      20
#define SKINS_DWMWA_WINDOW_CORNER_PREFERENCE     33
#define SKINS_DWMWA_BORDER_COLOR                 34
#define SKINS_DWMWCP_ROUND                       2

static bool setDwmAttribute( HWND hWnd, DWORD attribute, DWORD value )
{
    return SUCCEEDED( DwmSetWindowAttribute( hWnd, attribute, &value,
                                             sizeof( value ) ) );
}


/// Fading API"""), (
"""    m_pParent( pParentWindow ), m_type ( type )
{""",
"""    m_pParent( pParentWindow ), m_type ( type ), m_snappable( false ),
    m_selfMove( 0 ), m_hasRegion( false ), m_borderColor( CLR_INVALID )
{"""), (
"""        // top-level window (owned by the root window)
        HWND hWnd_owner = pFactory->getParentWindow();
        m_hWnd = CreateWindowEx( 0, vlc_class, vlc_name,
                                 WS_POPUP | WS_CLIPCHILDREN,
                                 0, 0, 0, 0, hWnd_owner, 0, hInst, NULL );
""",
"""        // top-level window (owned by the root window).
        // WS_THICKFRAME / WS_MAXIMIZEBOX make the window "arrangeable" for
        // Windows (Snap by dragging, Win+arrows, snap layouts); the frame is
        // removed in WM_NCCALCSIZE so the skin keeps drawing everything.
        // No WS_MINIMIZEBOX: minimizing goes through the root window, which
        // owns the taskbar button. A skin window minimized on its own
        // (Win+Down, "minimize all") stays on the desktop as a stub.
        HWND hWnd_owner = pFactory->getParentWindow();
        m_hWnd = CreateWindowEx( 0, vlc_class, vlc_name,
                                 WS_POPUP | WS_CLIPCHILDREN | WS_THICKFRAME |
                                 WS_SYSMENU | WS_MAXIMIZEBOX,
                                 0, 0, 0, 0, hWnd_owner, 0, hInst, NULL );
        m_snappable = true;

        // Windows 11 rounds the corners (and adds shadow and border) on its
        // own only for windows with a caption: ask for it. It shows while the
        // window has no region, see setSystemFrame().
        setDwmAttribute( m_hWnd, SKINS_DWMWA_WINDOW_CORNER_PREFERENCE,
                         SKINS_DWMWCP_ROUND );
"""), (
"""void Win32Window::toggleOnTop( bool onTop ) const
{
    SetWindowPos( m_hWnd, onTop ? HWND_TOPMOST : HWND_NOTOPMOST,
                  0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE );
}
""",
"""void Win32Window::toggleOnTop( bool onTop ) const
{
    SetWindowPos( m_hWnd, onTop ? HWND_TOPMOST : HWND_NOTOPMOST,
                  0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE );
}


bool Win32Window::startNativeMove() const
{
    if( !m_snappable )
        return false;

    // skins2 captured the mouse on button down; the system loop needs it
    ReleaseCapture();
    // SC_MOVE with the HTCAPTION hint starts the interactive move right away,
    // exactly like dragging a title bar: Snap, snap layouts, shake...
    // Returns when the mouse button is released.
    SendMessage( m_hWnd, WM_SYSCOMMAND, SC_MOVE | HTCAPTION, 0 );
    return true;
}


bool Win32Window::setMaximized( bool maximized ) const
{
    if( !m_snappable )
        return false;

    ShowWindow( m_hWnd, maximized ? SW_MAXIMIZE : SW_RESTORE );
    return true;
}


void Win32Window::setSystemFrame( bool systemFrame, COLORREF border ) const
{
    if( !systemFrame )
    {
        // shaped skin: the caller applies the region
        m_hasRegion = true;
        return;
    }

    if( m_hasRegion )
    {
        SetWindowRgn( m_hWnd, NULL, TRUE );
        m_hasRegion = false;
    }

    if( border != CLR_INVALID && border != m_borderColor )
    {
        m_borderColor = border;

        // Dark frame for a dark skin: it is what shows through while a
        // resized window waits for the skin to repaint
        DWORD dark = GetRValue( border ) * 299 + GetGValue( border ) * 587 +
                     GetBValue( border ) * 114 < 128000;
        if( !setDwmAttribute( m_hWnd, SKINS_DWMWA_USE_IMMERSIVE_DARK_MODE,
                              dark ) )
            setDwmAttribute( m_hWnd, SKINS_DWMWA_USE_IMMERSIVE_DARK_MODE_OLD,
                             dark );
        // Windows 11 draws its border over the outermost pixels of the
        // window: keep it in the colour of the skin
        setDwmAttribute( m_hWnd, SKINS_DWMWA_BORDER_COLOR, border );
    }
}
"""), (
"""void Win32Window::moveResize( int left, int top, int width, int height ) const
{
    MoveWindow( m_hWnd, left, top, width, height, TRUE );
}""",
"""void Win32Window::moveResize( int left, int top, int width, int height ) const
{
    // Mark this as a plugin-initiated geometry change: the WM_WINDOWPOSCHANGED
    // that MoveWindow sends synchronously must not be echoed back as if the
    // user had snapped or dragged the window.
    m_selfMove++;
    MoveWindow( m_hWnd, left, top, width, height, TRUE );
    m_selfMove--;
}""")])

# ------------------------------------------------------------------ Win32Graphics
patch("win32/win32_graphics.cpp", [(
"""    // Get window handle
    HWND hWnd = ((Win32Window&)rWindow).getHandle();

    // Apply the mask""",
"""    // Get window handle
    Win32Window &rWin = (Win32Window&)rWindow;
    HWND hWnd = rWin.getHandle();

    if( rWin.isSnappable() )
    {
        // A mask covering the whole image is a plain rectangular window: no
        // region then, because a region trades the frame rendered by the DWM
        // (shadow, rounded corners, border) for the legacy one. The border
        // takes the colour that the skin draws along its top edge.
        HRGN full = CreateRectRgn( 0, 0, m_width, m_height );
        bool isRect = EqualRgn( m_mask, full );
        DeleteObject( full );
        SelectClipRgn( m_hDC, NULL );
        rWin.setSystemFrame( isRect, GetPixel( m_hDC, m_width / 2, 0 ) );
        if( isRect )
            return;
    }

    // Apply the mask""")])

# ------------------------------------------------------------------ GenericWindow
patch("src/generic_window.hpp", [(
"""    /// windows handle
    vlc_wnd_type getOSHandle() const;
""",
"""    /// windows handle
    vlc_wnd_type getOSHandle() const;

    /// Snap support of the underlying OS window
    bool isSnappable() const;

    /// System driven drag (see OSWindow::startNativeMove)
    bool startNativeMove() const;

    /// System maximize / restore (see OSWindow::setMaximized)
    bool setMaximizedByOS( bool maximized ) const;

    /// True while the plugin itself is moving/resizing the OS window
    bool isSelfMoving() const;

    /// Called by the OS loop when the system changed the window geometry
    /// (snap, keyboard arrange, system drag, maximize): default does nothing
    virtual void onOSGeometryChange( int left, int top, int width, int height,
                                     bool maximized )
        { (void)left; (void)top; (void)width; (void)height; (void)maximized; }
""")])

patch("src/generic_window.cpp", [(
"""    SkinObject( pIntf ), m_left( left ), m_top( top ), m_width( 0 ),
    m_height( 0 ), m_pVarVisible( NULL )
{""",
"""    SkinObject( pIntf ), m_left( left ), m_top( top ), m_width( 0 ),
    m_height( 0 ), m_pOsWindow( NULL ), m_pVarVisible( NULL )
{"""), (
"""vlc_wnd_type GenericWindow::getOSHandle() const
{""",
"""bool GenericWindow::isSnappable() const
{
    return m_pOsWindow && m_pOsWindow->isSnappable();
}


bool GenericWindow::startNativeMove() const
{
    return m_pOsWindow && m_pOsWindow->startNativeMove();
}


bool GenericWindow::setMaximizedByOS( bool maximized ) const
{
    return m_pOsWindow && m_pOsWindow->setMaximized( maximized );
}


bool GenericWindow::isSelfMoving() const
{
    return m_pOsWindow && m_pOsWindow->isSelfMoving();
}


vlc_wnd_type GenericWindow::getOSHandle() const
{""")])

# ------------------------------------------------------------------ TopWindow
patch("src/top_window.hpp", [(
"""    /// Update the shape of the window from the active layout
    virtual void updateShape();
""",
"""    /// Update the shape of the window from the active layout
    virtual void updateShape();

    /// The system moved / resized / maximized the window: keep the skin,
    /// the active layout and the anchored windows in sync
    virtual void onOSGeometryChange( int left, int top, int width, int height,
                                     bool maximized );
"""), (
"""    /// Variable for the visibility of the window
    VarBoolImpl *m_pVarMaximized;
""",
"""    /// Variable for the visibility of the window
    VarBoolImpl *m_pVarMaximized;
    /// Guard against re-entrance while syncing with the OS geometry
    bool m_inGeometrySync = false;
""")])

patch("src/top_window.cpp", [(
"""void TopWindow::updateShape()
{""",
"""void TopWindow::onOSGeometryChange( int left, int top, int width, int height,
                                    bool maximized )
{
    if( m_inGeometrySync || !m_pActiveLayout || width <= 0 || height <= 0 )
        return;
    m_inGeometrySync = true;

    // Position: record it and drag the anchored windows along. During a
    // system driven drag the skin magnetism is applied once, at the end.
    if( left != getLeft() || top != getTop() )
        m_rWindowManager.syncMove( *this, left, top );

    // Size: adapt the active layout (min/max sizes are enforced there)
    if( width != m_pActiveLayout->getWidth() ||
        height != m_pActiveLayout->getHeight() )
        m_rWindowManager.syncResize( *m_pActiveLayout, width, height );

    if( m_pVarMaximized->get() != maximized )
        m_pVarMaximized->set( maximized );

    m_inGeometrySync = false;
}


void TopWindow::updateShape()
{""")])

# ------------------------------------------------------------------ WindowManager
patch("src/window_manager.hpp", [(
"""    /// Tell the window manager that a resize is initiated for rLayout
    void startResize( GenericLayout &rLayout, Direction_t direction );
""",
"""    /// The system moved rWindow (Snap, Win+arrows, system drag): record the
    /// new position and move the windows anchored to it by the same offset
    void syncMove( TopWindow &rWindow, int left, int top );

    /// The system resized the window of rLayout (Snap, Win+arrows, maximize,
    /// restore): give the layout that very size, without magnetism, and
    /// move the windows anchored to its right and bottom sides along
    void syncResize( GenericLayout &rLayout, int width, int height );

    /// A system driven drag of a window is in progress
    void setNativeMoving( bool b ) { m_nativeMoving = b; }
    bool isNativeMoving() const { return m_nativeMoving; }

    /// Tell the window manager that a resize is initiated for rLayout
    void startResize( GenericLayout &rLayout, Direction_t direction );
"""), (
"""     * If a new anchoring is detected, the windows will move (or resize)
     * accordingly.
     */
    void resize( GenericLayout &rLayout, int width, int height ) const;
""",
"""     * If a new anchoring is detected, the windows will move (or resize)
     * accordingly. Without magnetism the requested size is only checked
     * against the size limits of the layout.
     */
    void resize( GenericLayout &rLayout, int width, int height,
                 bool magnetism = true ) const;
"""), (
"""    /// Rect of the last maximized window
    SkinsRect m_maximizeRect;
""",
"""    /// Rect of the last maximized window
    SkinsRect m_maximizeRect;
    /// A system driven drag of a window is in progress
    bool m_nativeMoving = false;
""")])

patch("src/window_manager.cpp", [(
"""void WindowManager::startResize( GenericLayout &rLayout, Direction_t direction )
{""",
"""void WindowManager::syncMove( TopWindow &rWindow, int left, int top )
{
    int xOffset = left - rWindow.getLeft();
    int yOffset = top - rWindow.getTop();
    if( xOffset == 0 && yOffset == 0 )
        return;

    // Outside of a drag started by a control, build the set of hanging
    // windows (and apply the moving opacity) here
    bool ownSet = ( m_movingWindows.find( &rWindow ) == m_movingWindows.end() );
    if( ownSet )
        startMove( rWindow );

    WinSet_t::const_iterator it;
    for( it = m_movingWindows.begin(); it != m_movingWindows.end(); ++it )
    {
        if( *it == &rWindow )
        {
            // the system already placed this window: only record the position
            GenericWindow &rGeneric = rWindow;
            rGeneric.m_left = left;
            rGeneric.m_top = top;
        }
        else
        {
            (*it)->move( (*it)->getLeft() + xOffset,
                         (*it)->getTop() + yOffset );
        }
    }

    if( ownSet )
        stopMove();
}


void WindowManager::syncResize( GenericLayout &rLayout, int width, int height )
{
    // The magnetism is for a resize driven by the user. Here it would pull
    // the layout towards a screen edge or an anchor of another window, to a
    // size other than the one the system has just given to the window.
    startResize( rLayout, kResizeSE );
    resize( rLayout, width, height, false );
    stopResize();
}


void WindowManager::startResize( GenericLayout &rLayout, Direction_t direction )
{"""), (
"""void WindowManager::resize( GenericLayout &rLayout,
                            int width, int height ) const
{
    // TODO: handle anchored windows
    // Compute the real resizing offset
    int xOffset = width - rLayout.getWidth();
    int yOffset = height - rLayout.getHeight();

    // Check anchoring; this can change the values of xOffset and yOffset
    checkAnchors( rLayout.getWindow(), xOffset, yOffset );
""",
"""void WindowManager::resize( GenericLayout &rLayout,
                            int width, int height, bool magnetism ) const
{
    // TODO: handle anchored windows
    // Compute the real resizing offset
    int xOffset = width - rLayout.getWidth();
    int yOffset = height - rLayout.getHeight();

    // Check anchoring; this can change the values of xOffset and yOffset
    if( magnetism )
        checkAnchors( rLayout.getWindow(), xOffset, yOffset );
"""), (
"""    // Save the current position/size of the window, to be able to restore it
    m_maximizeRect = SkinsRect( rWindow.getLeft(), rWindow.getTop(),
                               rWindow.getLeft() + rWindow.getWidth(),
                               rWindow.getTop() + rWindow.getHeight() );
""",
"""    // Save the current position/size of the window, to be able to restore it
    m_maximizeRect = SkinsRect( rWindow.getLeft(), rWindow.getTop(),
                               rWindow.getLeft() + rWindow.getWidth(),
                               rWindow.getTop() + rWindow.getHeight() );

    // Let the system do it when possible: it keeps the restore geometry,
    // honours the work area and stays coherent with Win+Up / drag to top.
    // The layout and the "maximized" variable follow the OS notification.
    if( rWindow.setMaximizedByOS( true ) )
        return;
"""), (
"""void WindowManager::unmaximize( TopWindow &rWindow )
{
    // Register the window to allow moving it
//     registerWindow( rWindow );
""",
"""void WindowManager::unmaximize( TopWindow &rWindow )
{
    if( rWindow.setMaximizedByOS( false ) )
        return;

    // Register the window to allow moving it
//     registerWindow( rWindow );
""")])

# ------------------------------------------------------------------ CtrlMove
patch("controls/ctrl_move.cpp", [(
"""    m_pParent->m_xPos = pEvtMouse->getXPos();
    m_pParent->m_yPos = pEvtMouse->getYPos();

    m_pParent->captureMouse();

    m_pParent->m_rWindowManager.startMove( m_pParent->m_rWindow );
}""",
"""    m_pParent->m_xPos = pEvtMouse->getXPos();
    m_pParent->m_yPos = pEvtMouse->getYPos();

    WindowManager &rManager = m_pParent->m_rWindowManager;
    TopWindow &rWindow = m_pParent->m_rWindow;

    rManager.startMove( rWindow );

    // Let the system drive the drag when the platform supports it (Windows:
    // Snap to the screen edges, snap layouts, shake...). The anchored windows
    // follow through WindowManager::syncMove while the window moves.
    rManager.setNativeMoving( true );
    bool nativeDone = rWindow.startNativeMove();
    rManager.setNativeMoving( false );
    if( nativeDone )
    {
        // The system consumed the mouse release: apply the skin magnetism
        // once on the final position and finish the move
        rManager.move( rWindow, rWindow.getLeft(), rWindow.getTop() );
        rManager.stopMove();
        m_pParent->m_fsm.setState( "still" );
        return;
    }

    m_pParent->captureMouse();
}""")])

# ------------------------------------------------------------------ Win32Loop
patch("win32/win32_loop.cpp", [(
"""        default:
            break;
    }
    return DefWindowProc( hwnd, msg, wParam, lParam );;
}""",
"""        case WM_WINDOWPOSCHANGED:
        {
            // Snap, Win+arrows, system drag or maximize: keep the skin in sync.
            // Ignored while the plugin itself drives the geometry (self move),
            // and while the window is minimized.
            WINDOWPOS *pPos = (WINDOWPOS*)lParam;
            bool geomChanged = !(pPos->flags & SWP_NOMOVE) ||
                               !(pPos->flags & SWP_NOSIZE);
            if( win.isSnappable() && geomChanged && !win.isSelfMoving() &&
                !IsIconic( hwnd ) )
            {
                RECT rc;
                if( GetWindowRect( hwnd, &rc ) )
                    win.onOSGeometryChange( rc.left, rc.top,
                                            rc.right - rc.left,
                                            rc.bottom - rc.top,
                                            IsZoomed( hwnd ) != 0 );
            }
            break;
        }
        case WM_NCCALCSIZE:
        {
            // The sizing frame only exists to make the window snappable:
            // no non-client area, the skin draws the whole window
            if( win.isSnappable() )
                return 0;
            break;
        }
        case WM_NCACTIVATE:
        {
            // By default the system repaints the sizing frame at each
            // activation change, in the legacy style and straight over the
            // skin since there is no non-client area left: a light frame
            // around the window that loses the focus. lParam = -1 keeps the
            // activation processing and skips that repaint (a minimized
            // window is left to the default processing, as documented).
            if( win.isSnappable() && !IsIconic( hwnd ) )
                return DefWindowProc( hwnd, msg, wParam, (LPARAM)-1 );
            break;
        }
        case WM_NCPAINT:
        {
            // A window with a region (shaped skin) has no frame rendered by
            // the DWM: nothing may be painted here. Without region the
            // message must go on, the shadow of the window depends on it.
            RECT rgnBox;
            if( win.isSnappable() && GetWindowRgnBox( hwnd, &rgnBox ) != ERROR )
                return 0;
            break;
        }
        case 0x00AE: // WM_NCUAHDRAWCAPTION
        case 0x00AF: // WM_NCUAHDRAWFRAME
        {
            // Undocumented themed variants of the frame repaint
            if( win.isSnappable() )
                return 0;
            break;
        }
        case WM_NCHITTEST:
        {
            // No system borders or caption: the skin handles move and resize
            if( win.isSnappable() )
                return HTCLIENT;
            break;
        }
        case WM_GETMINMAXINFO:
        {
            // Maximize exactly to the work area of the current monitor
            if( win.isSnappable() )
            {
                HMONITOR hMon = MonitorFromWindow( hwnd,
                                                   MONITOR_DEFAULTTONEAREST );
                MONITORINFO mi;
                mi.cbSize = sizeof( mi );
                if( hMon && GetMonitorInfo( hMon, &mi ) )
                {
                    MINMAXINFO *pInfo = (MINMAXINFO*)lParam;
                    pInfo->ptMaxPosition.x = mi.rcWork.left - mi.rcMonitor.left;
                    pInfo->ptMaxPosition.y = mi.rcWork.top - mi.rcMonitor.top;
                    pInfo->ptMaxSize.x = mi.rcWork.right - mi.rcWork.left;
                    pInfo->ptMaxSize.y = mi.rcWork.bottom - mi.rcWork.top;
                    return 0;
                }
            }
            break;
        }
        case WM_CLOSE:
        {
            // System close request on a skin window: quit like the root window
            libvlc_Quit( getIntf()->obj.libvlc );
            return 0;
        }
        default:
            break;
    }
    return DefWindowProc( hwnd, msg, wParam, lParam );
}""")])

# ------------------------------------------------------------------ interfaccia web: comando della skin
# vlc.webInterface() apre nel browser la pagina dell'interfaccia HTTP di VLC (il telecomando web del kit)
patch("commands/cmd_minimize.hpp", [(
"""DEFINE_COMMAND( RemoveFromTaskBar, "remove from taskbar" )
""",
"""DEFINE_COMMAND( RemoveFromTaskBar, "remove from taskbar" )

/// Command to open the page of the HTTP interface in the default browser
DEFINE_COMMAND( WebInterface,      "web interface" )
""")])

patch("commands/cmd_minimize.cpp", [(
"""#include "../src/os_factory.hpp"
""",
"""#include "../src/os_factory.hpp"

#ifdef _WIN32
# include <shellapi.h>
#endif
"""), (
"""void CmdMinimize::execute()
{""",
"""void CmdWebInterface::execute()
{
#ifdef _WIN32
    // The HTTP interface listens on http-port (8080 unless changed)
    int port = (int)var_InheritInteger( getIntf(), "http-port" );
    wchar_t url[64];
    _snwprintf( url, 64, L"http://localhost:%d/", port );
    url[63] = L'\\0';
    INT_PTR ret = (INT_PTR)ShellExecuteW( NULL, L"open", url, NULL, NULL,
                                          SW_SHOWNORMAL );
    if( ret > 32 )
        msg_Dbg( getIntf(), "web interface opened in the browser (port %d)",
                 port );
    else
        msg_Warn( getIntf(), "cannot open the web interface (error %d)",
                  (int)ret );
#else
    msg_Warn( getIntf(), "opening the web interface is not supported here" );
#endif
}


void CmdMinimize::execute()
{""")])

patch("parser/interpreter.cpp", [(
"""    REGISTER_CMD( "vlc.quit()", CmdQuit )
""",
"""    REGISTER_CMD( "vlc.quit()", CmdQuit )
    REGISTER_CMD( "vlc.webInterface()", CmdWebInterface )
""")])

# ------------------------------------------------------------------ interfaccia web: indirizzi di rete del PC
# L'interfaccia HTTP (Lua) non ha modo di conoscere gli indirizzi del PC nella rete locale, che servono alla pagina
# per il riquadro "Collega il telefono": il modulo li pubblica in una variabile di libvlc. Lo script Lua fa scattare
# "skins2-lan-refresh" e poi legge "skins2-lan-addresses".
patch("src/skin_main.cpp", [(
"""#include <vlc_common.h>
#include <vlc_plugin.h>
""",
"""#ifdef _WIN32
# include <winsock2.h>
# include <ws2tcpip.h>
# include <iphlpapi.h>
# include <vector>
#endif

#include <vlc_common.h>
#include <vlc_plugin.h>
"""), (
"""//---------------------------------------------------------------------------
// Open: initialize interface
//---------------------------------------------------------------------------
""",
"""//---------------------------------------------------------------------------
// LAN addresses of this computer, for the web interface: the Lua HTTP
// interface cannot learn them by itself. A Lua script triggers
// "skins2-lan-refresh" on libvlc and then reads "skins2-lan-addresses": the
// IPv4 addresses separated by spaces, those of the adapters that have a
// default gateway (the ones another device of the network can reach) first.
//---------------------------------------------------------------------------
static int LanRefresh( vlc_object_t *p_obj, char const *, vlc_value_t,
                       vlc_value_t, void * )
{
    std::string list;
#ifdef _WIN32
    ULONG flags = GAA_FLAG_SKIP_ANYCAST | GAA_FLAG_SKIP_MULTICAST |
                  GAA_FLAG_SKIP_DNS_SERVER | GAA_FLAG_INCLUDE_GATEWAYS;
    ULONG size = 16 * 1024;
    std::vector<char> buf( size );
    ULONG ret = GetAdaptersAddresses( AF_INET, flags, NULL,
                    (IP_ADAPTER_ADDRESSES *)&buf[0], &size );
    if( ret == ERROR_BUFFER_OVERFLOW )
    {
        buf.resize( size );
        ret = GetAdaptersAddresses( AF_INET, flags, NULL,
                  (IP_ADAPTER_ADDRESSES *)&buf[0], &size );
    }
    for( int pass = 0; ret == NO_ERROR && pass < 2; pass++ )
    {
        for( IP_ADAPTER_ADDRESSES *p_ad = (IP_ADAPTER_ADDRESSES *)&buf[0];
             p_ad != NULL; p_ad = p_ad->Next )
        {
            if( p_ad->OperStatus != IfOperStatusUp ||
                p_ad->IfType == IF_TYPE_SOFTWARE_LOOPBACK ||
                ( p_ad->FirstGatewayAddress != NULL ) != ( pass == 0 ) )
                continue;
            for( IP_ADAPTER_UNICAST_ADDRESS *p_ua = p_ad->FirstUnicastAddress;
                 p_ua != NULL; p_ua = p_ua->Next )
            {
                if( p_ua->Address.lpSockaddr->sa_family != AF_INET )
                    continue;
                const unsigned char *b = (const unsigned char *)
                    &((struct sockaddr_in *)p_ua->Address.lpSockaddr)->sin_addr;
                if( b[0] == 127 || ( b[0] == 169 && b[1] == 254 ) )
                    continue; // loopback or self-assigned
                char psz_ip[16];
                snprintf( psz_ip, sizeof( psz_ip ), "%u.%u.%u.%u",
                          b[0], b[1], b[2], b[3] );
                if( !list.empty() )
                    list += ' ';
                list += psz_ip;
            }
        }
    }
#endif
    var_SetString( p_obj, "skins2-lan-addresses", list.c_str() );
    return VLC_SUCCESS;
}

//---------------------------------------------------------------------------
// Open: initialize interface
//---------------------------------------------------------------------------
"""), (
"""    vlc_mutex_lock( &skin_load.mutex );
    skin_load.intf = p_intf;
    vlc_mutex_unlock( &skin_load.mutex );

    return VLC_SUCCESS;
}""",
"""    vlc_mutex_lock( &skin_load.mutex );
    skin_load.intf = p_intf;
    vlc_mutex_unlock( &skin_load.mutex );

    // LAN addresses for the web interface (see LanRefresh)
    vlc_object_t *p_libvlc = VLC_OBJECT( p_intf->obj.libvlc );
    var_Create( p_libvlc, "skins2-lan-addresses", VLC_VAR_STRING );
    var_Create( p_libvlc, "skins2-lan-refresh", VLC_VAR_VOID );
    var_AddCallback( p_libvlc, "skins2-lan-refresh", LanRefresh, NULL );
    var_TriggerCallback( p_libvlc, "skins2-lan-refresh" );

    return VLC_SUCCESS;
}"""), (
"""    msg_Dbg( p_intf, "closing skins2 module" );
""",
"""    msg_Dbg( p_intf, "closing skins2 module" );

    vlc_object_t *p_libvlc = VLC_OBJECT( p_intf->obj.libvlc );
    var_DelCallback( p_libvlc, "skins2-lan-refresh", LanRefresh, NULL );
    var_Destroy( p_libvlc, "skins2-lan-refresh" );
    var_Destroy( p_libvlc, "skins2-lan-addresses" );
""")])

# ------------------------------------------------------------------ finestre di dialogo sopra il player
# Le finestre degli altri moduli di VLC (preferenze, apri media, informazioni...: le crea il modulo Qt, in un altro
# thread) non appartengono alla skin. Con il player "sempre in primo piano" si aprivano dietro di lui. Il modulo le
# segue con un WinEvent hook: le rende "in primo piano" finche' lo e' il player, e tiene le finestre della skin
# sempre sotto di loro (come le finestre di dialogo di una normale applicazione rispetto alla finestra principale).
# Due attenzioni, scoperte con una finestra di dialogo gia' aperta mentre si cambia il primo piano:
#  - SetWindowPos( HWND_TOPMOST ) arriva a WM_WINDOWPOSCHANGING come un normale spostamento in cima (hwndInsertAfter
#    vale 0, non HWND_TOPMOST), e Windows riordina nello stesso momento le altre finestre della skin (hanno lo stesso
#    proprietario). Mentre e' il modulo a cambiare il primo piano, il ciclo dei messaggi non deve toccare quell'ordine:
#    altrimenti rimette il player sotto la finestra di dialogo, che in primo piano non e' ancora, e il player resta
#    una finestra normale.
#  - Le finestre di dialogo seguono dopo che tutte le finestre della skin hanno cambiato stato (il gestore delle
#    finestre le cambia una alla volta): portate su prima, finirebbero sotto le ultime.
patch("win32/win32_factory.hpp", [(
"""#include <map>
""",
"""#include <map>
#include <set>
#include <vector>
"""), (
"""    HWND getParentWindow() { return m_hParentWindow; }
""",
"""    HWND getParentWindow() { return m_hParentWindow; }

    /// Dialogs of the other VLC modules (Qt): top-level windows of this
    /// process that do not belong to the skin. They follow the "always on
    /// top" status of the skin windows, once all of them have changed it...
    void setForeignOnTop( bool onTop );
    /// To be called around the change of that status for a skin window:
    /// meanwhile the loop leaves the Z order of the skin windows alone
    void beginOnTopChange() { m_onTopChange++; }
    void endOnTopChange() { m_onTopChange--; }
    bool isChangingOnTop() const { return m_onTopChange > 0; }
    /// ...and the skin windows are kept below them: lowest visible dialog
    /// in the Z order with the given topmost status, NULL if there is none
    HWND getLowestDialog( bool topmost ) const;
"""), (
"""    static BOOL CALLBACK MonitorEnumProc( HMONITOR hMonitor, HDC hdcMonitor,
                                          LPRECT lprcMonitor, LPARAM dwData );
private:""",
"""    static BOOL CALLBACK MonitorEnumProc( HMONITOR hMonitor, HDC hdcMonitor,
                                          LPRECT lprcMonitor, LPARAM dwData );
    /// Callback (windows of the other modules shown, hidden or destroyed)
    static void CALLBACK WinEventProc( HWINEVENTHOOK hHook, DWORD event,
                                       HWND hwnd, LONG idObject, LONG idChild,
                                       DWORD idThread, DWORD time );
private:
    /// A window of another module has been shown, hidden or destroyed
    void onForeignWindow( HWND hwnd, DWORD event );
    /// Give a foreign window the current "always on top" status
    void applyForeignOnTop( HWND hwnd );
    /// Give it to all the dialogs
    void applyForeignOnTopToAll();
    /// Hook on the windows of the other threads of the process
    HWINEVENTHOOK m_hWinEventHook;
    /// Current "always on top" status of the skin windows
    bool m_foreignOnTop;
    /// True when the dialogs have still to follow that status
    bool m_foreignPending;
    /// >0 while a skin window changes its "always on top" status
    int m_onTopChange;
    /// Visible dialogs of the other modules
    std::set<HWND> m_dialogs;
    /// Foreign windows made topmost by the skin (to be restored)
    std::set<HWND> m_madeTopmost;""")])

patch("win32/win32_factory.cpp", [(
"""Win32Factory::Win32Factory( intf_thread_t *pIntf ):
    OSFactory( pIntf ), m_hParentWindow( NULL ),
    m_dirSep( "\\\\" )
{""",
"""/// Factory that owns the WinEvent hook (one skins2 interface per process)
static Win32Factory *s_pHookOwner = NULL;


void CALLBACK Win32Factory::WinEventProc( HWINEVENTHOOK hHook, DWORD event,
                                          HWND hwnd, LONG idObject,
                                          LONG idChild, DWORD idThread,
                                          DWORD time )
{
    (void)hHook; (void)idThread; (void)time;
    if( s_pHookOwner != NULL && hwnd != NULL &&
        idObject == OBJID_WINDOW && idChild == CHILDID_SELF )
        s_pHookOwner->onForeignWindow( hwnd, event );
}


void Win32Factory::onForeignWindow( HWND hwnd, DWORD event )
{
    if( event != EVENT_OBJECT_SHOW )
    {
        // hidden or destroyed
        m_dialogs.erase( hwnd );
        if( event == EVENT_OBJECT_DESTROY )
            m_madeTopmost.erase( hwnd );
        return;
    }

    // Top-level windows only, and not the ones of the skin
    if( !IsWindow( hwnd ) || GetAncestor( hwnd, GA_ROOT ) != hwnd )
        return;
    LONG_PTR style = GetWindowLongPtr( hwnd, GWL_STYLE );
    if( style & WS_CHILD )
        return;
    TCHAR psz_class[64];
    if( !GetClassName( hwnd, psz_class, 64 ) ||
        !_tcscmp( psz_class, _T("SkinWindowClass") ) )
        return;

    bool isDialog = ( style & WS_CAPTION ) == WS_CAPTION;
    if( isDialog )
        m_dialogs.insert( hwnd );           // a dialog: preferences, open media...
    else if( _tcsncmp( psz_class, _T("Qt"), 2 ) )
        return;                             // not a menu or popup of the dialogs
    applyForeignOnTop( hwnd );

    // A dialog that is shown without being activated (VLC not in the
    // foreground) may sit below the skin windows, and the system does not
    // let it be raised: the skin windows above it go just below it instead.
    // Only among non-topmost windows (see WM_WINDOWPOSCHANGING).
    if( isDialog && !m_foreignOnTop &&
        !( GetWindowLongPtr( hwnd, GWL_EXSTYLE ) & WS_EX_TOPMOST ) )
    {
        std::vector<HWND> above;
        for( HWND h = GetTopWindow( NULL ); h != NULL && h != hwnd;
             h = GetWindow( h, GW_HWNDNEXT ) )
        {
            if( m_windowMap.count( h ) && IsWindowVisible( h ) &&
                !( GetWindowLongPtr( h, GWL_STYLE ) & WS_CHILD ) &&
                !( GetWindowLongPtr( h, GWL_EXSTYLE ) & WS_EX_TOPMOST ) )
                above.push_back( h );
        }
        // from the lowest one, to keep their order
        for( size_t i = above.size(); i-- > 0; )
            SetWindowPos( above[i], hwnd, 0, 0, 0, 0,
                          SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE );
    }
}


void Win32Factory::applyForeignOnTop( HWND hwnd )
{
    // Asynchronous: the window belongs to another thread, never wait for it
    const UINT flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE |
                       SWP_ASYNCWINDOWPOS;
    bool topmost = ( GetWindowLongPtr( hwnd, GWL_EXSTYLE ) & WS_EX_TOPMOST ) != 0;
    if( m_foreignOnTop )
    {
        if( !topmost )
            m_madeTopmost.insert( hwnd );
        // also when it is topmost already: back above the skin windows
        if( !topmost || m_madeTopmost.count( hwnd ) )
            SetWindowPos( hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags );
    }
    else if( m_madeTopmost.erase( hwnd ) && topmost )
    {
        SetWindowPos( hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags );
    }
}


void Win32Factory::setForeignOnTop( bool onTop )
{
    m_foreignOnTop = onTop;

    // The window manager changes the skin windows one after the other, and
    // each of them calls this: the dialogs follow once, when all are done.
    // Raised at the first call, they would end below the last skin windows.
    if( m_foreignPending )
        return;
    if( PostMessage( m_hParentWindow, MY_WM_FOREIGNONTOP, 0, 0 ) )
        m_foreignPending = true;
    else
        applyForeignOnTopToAll();
}


void Win32Factory::applyForeignOnTopToAll()
{
    m_foreignPending = false;
    // the visible dialogs, and the hidden ones that were made topmost: Qt
    // hides its dialogs and shows the same windows again later
    std::set<HWND> dialogs = m_dialogs;
    dialogs.insert( m_madeTopmost.begin(), m_madeTopmost.end() );
    for( std::set<HWND>::const_iterator it = dialogs.begin();
         it != dialogs.end(); ++it )
    {
        if( IsWindow( *it ) )
            applyForeignOnTop( *it );
    }
}


HWND Win32Factory::getLowestDialog( bool topmost ) const
{
    if( m_dialogs.empty() )
        return NULL;
    HWND hLowest = NULL;
    for( HWND h = GetTopWindow( NULL ); h != NULL;
         h = GetWindow( h, GW_HWNDNEXT ) )
    {
        if( m_dialogs.count( h ) && IsWindowVisible( h ) && !IsIconic( h ) &&
            ( ( GetWindowLongPtr( h, GWL_EXSTYLE ) & WS_EX_TOPMOST ) != 0 ) == topmost )
            hLowest = h;
    }
    return hLowest;
}


Win32Factory::Win32Factory( intf_thread_t *pIntf ):
    OSFactory( pIntf ), m_hParentWindow( NULL ),
    m_dirSep( "\\\\" ), m_hWinEventHook( NULL ), m_foreignOnTop( false ),
    m_foreignPending( false ), m_onTopChange( 0 )
{"""), (
"""// Custom message for the notifications of the system tray
#define MY_WM_TRAYACTION (WM_APP + 1)
""",
"""// Custom message for the notifications of the system tray
#define MY_WM_TRAYACTION (WM_APP + 1)
// Custom message: the dialogs have to follow the "always on top" status
#define MY_WM_FOREIGNONTOP (WM_APP + 2)
"""), (
"""        // Handle systray notifications
        else if( uMsg == MY_WM_TRAYACTION )
        {""",
"""        else if( uMsg == MY_WM_FOREIGNONTOP )
        {
            pFactory->applyForeignOnTopToAll();
            return 0;
        }
        // Handle systray notifications
        else if( uMsg == MY_WM_TRAYACTION )
        {"""), (
"""    // All went well
    return true;
}""",
"""    // Windows of the other modules (Qt dialogs), which live in other threads:
    // the notifications are delivered to this thread by its message loop
    s_pHookOwner = this;
    m_hWinEventHook = SetWinEventHook( EVENT_OBJECT_DESTROY, EVENT_OBJECT_HIDE,
                                       NULL, Win32Factory::WinEventProc,
                                       GetCurrentProcessId(), 0,
                                       WINEVENT_OUTOFCONTEXT |
                                       WINEVENT_SKIPOWNTHREAD );
    if( m_hWinEventHook == NULL )
        msg_Warn( getIntf(), "cannot follow the windows of the dialogs" );

    // All went well
    return true;
}"""), (
"""    // Remove the systray icon
    removeFromTray();
""",
"""    // Remove the systray icon
    removeFromTray();

    if( m_hWinEventHook )
        UnhookWinEvent( m_hWinEventHook );
    if( s_pHookOwner == this )
        s_pHookOwner = NULL;
""")])

patch("win32/win32_window.cpp", [(
"""void Win32Window::toggleOnTop( bool onTop ) const
{
    SetWindowPos( m_hWnd, onTop ? HWND_TOPMOST : HWND_NOTOPMOST,
                  0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE );
}""",
"""void Win32Window::toggleOnTop( bool onTop ) const
{
    Win32Factory *pFactory =
        (Win32Factory*)Win32Factory::instance( getIntf() );

    // The window receives this request as an ordinary move to the top of
    // the Z order, and the system moves the other skin windows along: the
    // loop must not mistake it for a window that is raised (see
    // WM_WINDOWPOSCHANGING)
    pFactory->beginOnTopChange();
    SetWindowPos( m_hWnd, onTop ? HWND_TOPMOST : HWND_NOTOPMOST,
                  0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE );
    pFactory->endOnTopChange();

    // The dialogs of VLC follow, and go back above the skin windows
    if( m_snappable )
        pFactory->setForeignOnTop( onTop );
}""")])

patch("win32/win32_loop.cpp", [(
"""        case WM_WINDOWPOSCHANGED:
        {
            // Snap, Win+arrows, system drag or maximize: keep the skin in sync.""",
"""        case WM_WINDOWPOSCHANGING:
        {
            // The dialogs of VLC stay above the skin windows, as the dialogs
            // of an application above its main window: a skin window that
            // is raised goes just below the lowest of them. Only among
            // windows with the same topmost status, otherwise the insertion
            // would change the status of the skin window. Not while the
            // skin itself changes that status: the request comes here as a
            // move to the top (hwndInsertAfter is not HWND_TOPMOST), and
            // kept below a dialog that is not topmost yet it would be lost.
            WINDOWPOS *pPos = (WINDOWPOS*)lParam;
            if( win.isSnappable() && !pFactory->isChangingOnTop() &&
                !( pPos->flags & SWP_NOZORDER ) &&
                pPos->hwndInsertAfter != HWND_TOPMOST &&
                pPos->hwndInsertAfter != HWND_NOTOPMOST &&
                pPos->hwndInsertAfter != HWND_BOTTOM )
            {
                bool topmost = ( GetWindowLongPtr( hwnd, GWL_EXSTYLE ) &
                                 WS_EX_TOPMOST ) != 0;
                HWND hDialog = pFactory->getLowestDialog( topmost );
                if( hDialog != NULL )
                    pPos->hwndInsertAfter = hDialog;
            }
            break;
        }
        case WM_WINDOWPOSCHANGED:
        {
            // Snap, Win+arrows, system drag or maximize: keep the skin in sync.""")])

# ------------------------------------------------------------------ ridisegno veloce durante il ridimensionamento
# A ogni passo di ridimensionamento skins2 ridisegna tutto il layout via software. Pochi punti costavano quasi tutto
# il tempo (da 20 a 60 ms per passo, cioe' una finestra che si ridimensiona "a tratti"):
#  - ScaledBitmap ricalcolava pixel per pixel anche le righe identiche alla precedente (uno sfondo di 4x4 pixel
#    stirato su tutta la finestra);
#  - CtrlSliderBg riscalava l'intera sequenza di immagini della barra (centinaia di fotogrammi) invece del solo
#    fotogramma da disegnare;
#  - Win32Graphics::drawBitmap costruiva la maschera di trasparenza con un'operazione sulle regioni per ogni segmento
#    di ogni riga, e passava da AlphaBlend anche le immagini senza trasparenza.
# Il risultato disegnato e' identico, pixel per pixel.
patch("src/scaled_bitmap.hpp", [(
"""    ScaledBitmap( intf_thread_t *pIntf, const GenericBitmap &rBitmap,
                  int width, int height );
""",
"""    ScaledBitmap( intf_thread_t *pIntf, const GenericBitmap &rBitmap,
                  int width, int height );

    /// Create only a part of it: the rectangle (xPart, yPart, partWidth,
    /// partHeight) of the given bitmap scaled to width x height
    ScaledBitmap( intf_thread_t *pIntf, const GenericBitmap &rBitmap,
                  int width, int height,
                  int xPart, int yPart, int partWidth, int partHeight );
"""), (
"""    /// Image data buffer
    uint8_t *m_pData;
""",
"""    /// Image data buffer
    uint8_t *m_pData;

    /// Fill the buffer with the part starting at (xPart, yPart) of the given
    /// bitmap scaled to width x height
    void scale( const GenericBitmap &rBitmap, int width, int height,
                int xPart, int yPart );
""")])

patch_between("src/scaled_bitmap.cpp", '#include "scaled_bitmap.hpp"\n', "ScaledBitmap::~ScaledBitmap()",
"""#include "scaled_bitmap.hpp"
#include <cstring>
#include <vector>


ScaledBitmap::ScaledBitmap( intf_thread_t *pIntf, const GenericBitmap &rBitmap,
                            int width, int height ):
    GenericBitmap( pIntf ), m_width( width ), m_height( height )
{
    scale( rBitmap, width, height, 0, 0 );
}


ScaledBitmap::ScaledBitmap( intf_thread_t *pIntf, const GenericBitmap &rBitmap,
                            int width, int height,
                            int xPart, int yPart,
                            int partWidth, int partHeight ):
    GenericBitmap( pIntf ), m_width( partWidth ), m_height( partHeight )
{
    scale( rBitmap, width, height, xPart, yPart );
}


void ScaledBitmap::scale( const GenericBitmap &rBitmap, int width, int height,
                          int xPart, int yPart )
{
    // XXX We should check that width and height are positive...

    // Allocate memory for the buffer
    m_pData = new uint8_t[m_height * m_width * 4];

    int srcWidth = rBitmap.getWidth();
    int srcHeight = rBitmap.getHeight();
    const uint32_t *pSrcData = (const uint32_t*)rBitmap.getData();
    uint32_t *pDestData = (uint32_t*)m_pData;
    if( m_width <= 0 || m_height <= 0 || width <= 0 || height <= 0 ||
        xPart < 0 || yPart < 0 || xPart + m_width > width )
        return;

    // The horizontal mapping is the same on every line: source column of
    // each destination column, computed once (Bresenham algorithm)
    std::vector<int> column( width );
    if( width > srcWidth )
    {
        // Horizontal enlargement
        int incX1 = 2 * (srcWidth-1);
        int incX2 = incX1 - 2 * (width-1);
        int dX = incX1 - (width-1);
        int src = 0;
        for( int x = 0; x < width; x++ )
        {
            column[x] = src;
            if( dX <= 0 )
            {
                dX += incX1;
            }
            else
            {
                dX += incX2;
                src++;
            }
        }
    }
    else if( width == 1 )
    {
        column[0] = 0;
    }
    else
    {
        // Horizontal reduction
        int incX1 = 2 * (width-1);
        int incX2 = incX1 - 2 * (srcWidth-1);
        int dX = incX1 - (srcWidth-1);
        int src = 0;
        for( int x = 0; x < width; x++ )
        {
            column[x] = src++;
            while( dX <= 0 )
            {
                dX += incX1;
                src++;
            }
            dX += incX2;
        }
    }
    for( int x = 0; x < width; x++ )
    {
        if( column[x] >= srcWidth )
            column[x] = srcWidth - 1;
    }

    // A line that comes from the same source line as the previous one is a
    // copy of it: the usual case when a small bitmap is stretched
    const int *pColumn = &column[xPart];
    int prevSrcY = -1;
    for( int y = 0; y < m_height; y++ )
    {
        int srcY = ((y + yPart) * srcHeight) / height;
        uint32_t *pLine = pDestData + y * m_width;
        if( srcY == prevSrcY )
        {
            memcpy( pLine, pLine - m_width, m_width * sizeof( uint32_t ) );
            continue;
        }
        const uint32_t *pSrcLine = pSrcData + srcY * srcWidth;
        for( int x = 0; x < m_width; x++ )
        {
            pLine[x] = pSrcLine[pColumn[x]];
        }
        prevSrcY = srcY;
    }
}


ScaledBitmap::~ScaledBitmap()""")

patch("controls/ctrl_slider.hpp", [(
"""    /// Scaled bitmap if needed
    ScaledBitmap *m_pScaledBmp;
""",
"""    /// Scaled image of the current position, built when it is drawn
    ScaledBitmap *m_pScaledBmp;
    /// Position that m_pScaledBmp has been built for
    int m_scaledPosition;
    /// Size of the whole image sequence once scaled
    int m_seqWidth, m_seqHeight;
""")])

patch("controls/ctrl_slider.cpp", [(
"""    m_pImgSeq( pBackground ), m_pScaledBmp( NULL ),
""",
"""    m_pImgSeq( pBackground ), m_pScaledBmp( NULL ), m_scaledPosition( -1 ),
    m_seqWidth( 0 ), m_seqHeight( 0 ),
"""), (
"""    if( m_pScaledBmp )
    {
        // background size that is displayed""",
"""    if( m_pImgSeq )
    {
        // background size that is displayed"""), (
"""    if( !m_pScaledBmp || m_bgWidth <= 0 || m_bgHeight <= 0 )
        return;
""",
"""    if( !m_pImgSeq || m_bgWidth <= 0 || m_bgHeight <= 0 )
        return;
"""), (
"""    rect clip( xDest, yDest, w, h );
    rect inter;
    if( rect::intersect( region, clip, &inter ) )
        rImage.drawBitmap( *m_pScaledBmp,
                           x + inter.x - region.x,
                           y + inter.y - region.y,
                           inter.x, inter.y,
                           inter.width, inter.height );
}""",
"""    rect clip( xDest, yDest, w, h );
    rect inter;
    if( !rect::intersect( region, clip, &inter ) )
        return;

    // Only the image of the current position is scaled, and only when it
    // changes: scaling the whole sequence (hundreds of images) at each step
    // of a resize made the resizing of the window jerky
    if( !m_pScaledBmp || m_scaledPosition != m_position )
    {
        delete m_pScaledBmp;
        m_pScaledBmp = NULL;
        int partWidth = __MIN( region.width, m_seqWidth - x );
        int partHeight = __MIN( region.height, m_seqHeight - y );
        if( partWidth <= 0 || partHeight <= 0 )
            return;
        m_pScaledBmp = new ScaledBitmap( getIntf(), *m_pImgSeq,
                                         m_seqWidth, m_seqHeight,
                                         x, y, partWidth, partHeight );
        m_scaledPosition = m_position;
    }
    rImage.drawBitmap( *m_pScaledBmp,
                       inter.x - region.x, inter.y - region.y,
                       inter.x, inter.y, inter.width, inter.height );
}"""), (
"""    if( !m_pScaledBmp ||
        m_pScaledBmp->getWidth() != width ||
        m_pScaledBmp->getHeight() != height )
    {
        // scaled bitmap
        delete m_pScaledBmp;
        m_pScaledBmp = new ScaledBitmap( getIntf(), *m_pImgSeq, width, height );
    }""",
"""    if( width != m_seqWidth || height != m_seqHeight )
    {
        // the scaled image is built again by draw()
        m_seqWidth = width;
        m_seqHeight = height;
        delete m_pScaledBmp;
        m_pScaledBmp = NULL;
    }""")])

patch("win32/win32_graphics.cpp", [(
"""#include "../src/generic_bitmap.hpp"
""",
"""#include "../src/generic_bitmap.hpp"
#include <cstring>
#include <vector>
""")])

patch_between("win32/win32_graphics.cpp", "    void *pBits;     // pointer to DIB section\n",
"""    // Do cleanup
    DeleteObject( hBmp );
    DeleteObject( mask );
    DeleteDC( hDC );
}
""",
"""    // Visible segments of each line, for the transparency mask. They are
    // gathered and turned into a region in one go: one region operation per
    // segment is very slow on large bitmaps and on detailed ones (texts).
    std::vector<RECT> segments;
    // No transparency at all: the bitmap is copied as it is
    bool opaque = true;
    // Index of the segment of the previous line, when it had only one
    int prevSingle = -1;

    // Skip the first lines of the image
    pBmpData += 4 * ySrc * rBitmap.getWidth();
    const uint8_t *pFirstLine = pBmpData;

    for( int y = 0; y < height; y++ )
    {
        // Pixels of the line: B,G,R,A bytes, alpha in the high-order byte
        const uint32_t *pPixels = (const uint32_t*)( pBmpData + 4 * xSrc );
        int first = (int)segments.size();

        uint32_t all = 0xff000000;
        for( int x = 0; x < width; x++ )
            all &= pPixels[x];
        if( all == 0xff000000 )
        {
            // Opaque line: one segment
            RECT r = { 0, y, width, y + 1 };
            segments.push_back( r );
        }
        else
        {
            opaque = false;
            int x = 0;
            while( x < width )
            {
                // Skip the transparent pixels
                while( x < width && ( pPixels[x] >> 24 ) == 0 )
                    x++;
                if( x >= width )
                    break;
                // Visible segment
                RECT r = { x, y, x, y + 1 };
                while( x < width && ( pPixels[x] >> 24 ) != 0 )
                    x++;
                r.right = x;
                segments.push_back( r );
            }
        }

        // Same single segment as the line above: one taller rectangle
        if( (int)segments.size() == first + 1 )
        {
            if( prevSingle >= 0 &&
                segments[prevSingle].left == segments[first].left &&
                segments[prevSingle].right == segments[first].right )
            {
                segments[prevSingle].bottom = y + 1;
                segments.pop_back();
            }
            else
            {
                prevSingle = first;
            }
        }
        else
        {
            prevSingle = -1;
        }

        pBmpData += 4 * rBitmap.getWidth();
    }

    // Mask for transparency
    HRGN mask = NULL;
    if( segments.size() == 1 )
    {
        mask = CreateRectRgnIndirect( &segments[0] );
    }
    else if( segments.size() > 1 )
    {
        // The segments are sorted from top to bottom and from left to right
        std::vector<char> buffer( sizeof( RGNDATAHEADER ) +
                                  segments.size() * sizeof( RECT ) );
        RGNDATA *pRgnData = (RGNDATA*)&buffer[0];
        pRgnData->rdh.dwSize = sizeof( RGNDATAHEADER );
        pRgnData->rdh.iType = RDH_RECTANGLES;
        pRgnData->rdh.nCount = (DWORD)segments.size();
        pRgnData->rdh.nRgnSize = 0;
        SetRect( &pRgnData->rdh.rcBound, 0, 0, width, height );
        memcpy( pRgnData->Buffer, &segments[0],
                segments.size() * sizeof( RECT ) );
        mask = ExtCreateRegion( NULL, (DWORD)buffer.size(), pRgnData );
    }
    if( mask == NULL )
    {
        mask = CreateRectRgn( 0, 0, 0, 0 );
        for( size_t i = 0; i < segments.size(); i++ )
        {
            addSegmentInRegion( mask, segments[i].left, segments[i].right,
                                segments[i].top );
            for( int y = segments[i].top + 1; y < segments[i].bottom; y++ )
                addSegmentInRegion( mask, segments[i].left,
                                    segments[i].right, y );
        }
    }

    // Apply the mask to the internal DC
    OffsetRgn( mask, xDest, yDest );
    SelectClipRgn( m_hDC, mask );

    // Fill a BITMAPINFO structure
    BITMAPINFO bmpInfo;
    memset( &bmpInfo, 0, sizeof( bmpInfo ) );
    bmpInfo.bmiHeader.biSize = sizeof( BITMAPINFOHEADER );
    bmpInfo.bmiHeader.biHeight = -height;
    bmpInfo.bmiHeader.biPlanes = 1;
    bmpInfo.bmiHeader.biBitCount = 32;
    bmpInfo.bmiHeader.biCompression = BI_RGB;

    if( opaque )
    {
        // Nothing to blend: the lines go from the buffer of the bitmap to
        // the internal DC, described as a bitmap of their own (the buffer
        // has the layout of a top-down 32 bits DIB)
        bmpInfo.bmiHeader.biWidth = rBitmap.getWidth();
        bmpInfo.bmiHeader.biSizeImage = rBitmap.getWidth() * height * 4;
        SetDIBitsToDevice( m_hDC, xDest, yDest, width, height, xSrc, 0,
                           0, height, pFirstLine, &bmpInfo, DIB_RGB_COLORS );
    }
    else
    {
        // Create a DIB (Device Independent Bitmap) and associate it with
        // a temporary DC
        void *pBits;     // pointer to DIB section
        bmpInfo.bmiHeader.biWidth = width;
        bmpInfo.bmiHeader.biSizeImage = width * height * 4;
        HDC hDC = CreateCompatibleDC( m_hDC );
        HBITMAP hBmp = CreateDIBSection( hDC, &bmpInfo, DIB_RGB_COLORS,
                                         &pBits, NULL, 0 );
        SelectObject( hDC, hBmp );

        // Copy the bitmap on the image
        for( int y = 0; y < height; y++ )
        {
            memcpy( (uint32_t*)pBits + y * width,
                    pFirstLine + 4 * ( y * rBitmap.getWidth() + xSrc ),
                    4 * width );
        }

        BLENDFUNCTION bf;      // structure for alpha blending
        bf.BlendOp = AC_SRC_OVER;
        bf.BlendFlags = 0;
        bf.SourceConstantAlpha = 0xff;  // don't use constant alpha
        bf.AlphaFormat = AC_SRC_ALPHA;

        // Blend the image onto the internal DC
        if( !AlphaBlend( m_hDC, xDest, yDest, width, height, hDC, 0, 0,
                         width, height, bf ) )
        {
            msg_Err( getIntf(), "AlphaBlend() failed" );
        }

        DeleteObject( hBmp );
        DeleteDC( hDC );
    }

    // Add the bitmap mask to the global graphics mask
    CombineRgn( m_mask, m_mask, mask, RGN_OR );

    // Do cleanup
    DeleteObject( mask );
}
""")

# Lo sfondo delle skin e' di solito una piccola immagine a tinta unita stirata (resize="scale") su tutta la finestra:
# stirata, e' un rettangolo pieno. Non c'e' niente da riscalare a ogni passo, basta riempire.
patch("controls/ctrl_image.hpp", [(
"""    /// offset for image inside the control
    int m_x;
    int m_y;
""",
"""    /// offset for image inside the control
    int m_x;
    int m_y;
    /// true when the bitmap is one opaque colour and is stretched to the
    /// size of the control: a filled rectangle, with nothing to scale
    bool m_plain;
    /// that colour (#RRGGBB)
    uint32_t m_plainColor;

    /// Look whether the bitmap is one opaque colour
    void checkPlain();
""")])

patch("controls/ctrl_image.cpp", [(
"""    m_x( 0 ), m_y( 0 )
{""",
"""    m_x( 0 ), m_y( 0 ), m_plain( false ), m_plainColor( 0 )
{"""), (
"""                                    m_pBitmap->getWidth(),
                                    m_pBitmap->getHeight() );
    m_pImage->drawBitmap( *m_pBitmap );
}


CtrlImage::~CtrlImage()""",
"""                                    m_pBitmap->getWidth(),
                                    m_pBitmap->getHeight() );
    m_pImage->drawBitmap( *m_pBitmap );
    checkPlain();
}


void CtrlImage::checkPlain()
{
    m_plain = false;
    const uint32_t *pData = (const uint32_t*)m_pBitmap->getData();
    int count = m_pBitmap->getWidth() * m_pBitmap->getHeight();
    if( m_resizeMethod != kScale || pData == NULL || count <= 0 ||
        ( pData[0] >> 24 ) != 0xff )
        return;
    for( int i = 1; i < count; i++ )
    {
        if( pData[i] != pData[0] )
            return;
    }
    m_plain = true;
    m_plainColor = pData[0] & 0xffffff;
}


CtrlImage::~CtrlImage()"""), (
"""        case kScale:
            break;
        }
        return m_pImage->hit( x, y );""",
"""        case kScale:
            if( m_plain )
                return true;
            break;
        }
        return m_pImage->hit( x, y );"""), (
"""    if( m_resizeMethod == kScale )
    {
        // Use scaling method
        if( width != m_pImage->getWidth() ||""",
"""    if( m_resizeMethod == kScale && m_plain )
    {
        // One colour stretched to the size of the control (the usual
        // background of a window): scaling it at each step of a resize is
        // what took most of the time
        rImage.fillRect( inter.x, inter.y, inter.width, inter.height,
                         m_plainColor );
    }
    else if( m_resizeMethod == kScale )
    {
        // Use scaling method
        if( width != m_pImage->getWidth() ||"""), (
"""                                        m_pBitmap->getWidth(),
                                        m_pBitmap->getHeight() );
        m_pImage->drawBitmap( *m_pBitmap );

        notifyLayout();""",
"""                                        m_pBitmap->getWidth(),
                                        m_pBitmap->getHeight() );
        m_pImage->drawBitmap( *m_pBitmap );
        checkPlain();

        notifyLayout();""")])

# ------------------------------------------------------------------ ridimensionamento da tutti i lati, fatto da Windows
# Una finestra che disegna da se' la propria cornice perde il ridimensionamento standard e deve restituirlo con
# WM_NCHITTEST ("Custom Window Frame Using DWM", Microsoft Learn). Fin qui il modulo rispondeva sempre HTCLIENT e la
# finestra si ridimensionava solo dalle maniglie disegnate dalla skin (destra, basso, angolo), con il ciclo della
# skin: un comando in coda ogni 10 ms e l'intero layout ridisegnato due volte.
#  - I bordi di ridimensionamento della cornice (sinistra, destra, basso) restano alla finestra: WM_NCCALCSIZE toglie
#    solo quello in alto. Windows li lascia invisibili e sono l'area, appena fuori dalla finestra, da cui la si
#    ridimensiona, come per ogni finestra di Windows 10 e 11; funzionano anche sopra il video, che copre i bordi
#    dell'area disegnata dalla skin. In alto, dove il bordo non c'e', l'area e' la fascia in cima alla barra del
#    titolo, come nelle applicazioni che disegnano la propria barra (Terminale, Blocco note...).
#  - Le maniglie della skin rispondono con lo stesso codice (HTRIGHT, HTBOTTOM, HTBOTTOMRIGHT): un solo percorso,
#    quello di sistema, con i suoi cursori.
#  - WM_GETMINMAXINFO da' a Windows le misure minime e massime del layout, che cosi' valgono anche per Snap.
#  - La skin continua a ragionare sull'area che disegna (l'area client): Win32Window::moveResize aggiunge i bordi,
#    WM_WINDOWPOSCHANGED li toglie, e la sagoma delle skin sagomate viene spostata di conseguenza.
patch("controls/ctrl_generic.hpp", [(
"""    /// Return true if the control can be scrollable
    virtual bool isScrollable() const { return false; }
""",
"""    /// Return true if the control can be scrollable
    virtual bool isScrollable() const { return false; }

    /// Direction of the resizing done by dragging the control (a
    /// WindowManager::Direction_t value), -1 if it is not a resize handle
    virtual int getResizeDirection() const { return -1; }
""")])

patch("controls/ctrl_resize.hpp", [(
"""    /// Get the type of control (custom RTTI)
    virtual std::string getType() const { return m_rCtrl.getType(); }
""",
"""    /// Get the type of control (custom RTTI)
    virtual std::string getType() const { return m_rCtrl.getType(); }

    /// Direction of the resizing done by dragging the control
    virtual int getResizeDirection() const { return m_direction; }
""")])

patch("src/generic_window.hpp", [(
"""    /// reparent
    void setParent( GenericWindow* pParent,
                    int x = 0, int y = 0, int w = -1, int h = -1 );
""",
"""    /// Smallest and largest size that the window can be given; false if
    /// it cannot be resized
    virtual bool getSizeLimits( int *pMinWidth, int *pMinHeight,
                                int *pMaxWidth, int *pMaxHeight ) const
    {
        (void)pMinWidth; (void)pMinHeight; (void)pMaxWidth; (void)pMaxHeight;
        return false;
    }

    /// Resize handle of the skin at the given position in the window: a
    /// WindowManager::Direction_t value, -1 if there is none
    virtual int getResizeHandle( int xPos, int yPos ) const
        { (void)xPos; (void)yPos; return -1; }

    /// reparent
    void setParent( GenericWindow* pParent,
                    int x = 0, int y = 0, int w = -1, int h = -1 );
""")])

patch("src/top_window.hpp", [(
"""    /// Called by a control that wants to capture the mouse
    virtual void onControlCapture( const CtrlGeneric &rCtrl );
""",
"""    /// Size limits of the active layout
    virtual bool getSizeLimits( int *pMinWidth, int *pMinHeight,
                                int *pMaxWidth, int *pMaxHeight ) const;

    /// Resize handle of the active layout at the given position
    virtual int getResizeHandle( int xPos, int yPos ) const;

    /// Called by a control that wants to capture the mouse
    virtual void onControlCapture( const CtrlGeneric &rCtrl );
""")])

patch("src/top_window.cpp", [(
"""void TopWindow::updateShape()
{""",
"""bool TopWindow::getSizeLimits( int *pMinWidth, int *pMinHeight,
                               int *pMaxWidth, int *pMaxHeight ) const
{
    if( m_pActiveLayout == NULL )
        return false;

    *pMinWidth = m_pActiveLayout->getMinWidth();
    *pMinHeight = m_pActiveLayout->getMinHeight();
    *pMaxWidth = m_pActiveLayout->getMaxWidth();
    *pMaxHeight = m_pActiveLayout->getMaxHeight();
    return true;
}


int TopWindow::getResizeHandle( int xPos, int yPos ) const
{
    if( m_pActiveLayout == NULL )
        return -1;

    // Uppermost control at this position, as findHitControl() finds it
    // (but nothing is told to the controls here)
    const std::list<LayeredControl> &ctrlList = m_pActiveLayout->getControlList();
    std::list<LayeredControl>::const_reverse_iterator iter;
    for( iter = ctrlList.rbegin(); iter != ctrlList.rend(); ++iter )
    {
        CtrlGeneric *pCtrl = (*iter).m_pControl;
        const Position *pos = pCtrl->getPosition();
        if( pos != NULL && pCtrl->isVisible() &&
            pCtrl->mouseOver( xPos - pos->getLeft(), yPos - pos->getTop() ) )
        {
            return pCtrl->getResizeDirection();
        }
    }
    return -1;
}


void TopWindow::updateShape()
{""")])

patch("win32/win32_window.hpp", [(
"""    /// See OSWindow::isSelfMoving
    virtual bool isSelfMoving() const { return m_selfMove > 0; }
""",
"""    /// See OSWindow::isSelfMoving
    virtual bool isSelfMoving() const { return m_selfMove > 0; }

    /// Thickness of the sizing borders that a snappable window keeps on its
    /// left, right and bottom sides (none at the top). The system leaves
    /// them invisible; they lie around the area that the skin draws and
    /// are where the window is resized from.
    static void getSizingBorders( HWND hWnd, RECT *pBorders );
""")])

patch("win32/win32_window.cpp", [(
"""void Win32Window::moveResize( int left, int top, int width, int height ) const
{
    // Mark this as a plugin-initiated geometry change: the WM_WINDOWPOSCHANGED
    // that MoveWindow sends synchronously must not be echoed back as if the
    // user had snapped or dragged the window.
    m_selfMove++;
    MoveWindow( m_hWnd, left, top, width, height, TRUE );
    m_selfMove--;
}""",
"""void Win32Window::getSizingBorders( HWND hWnd, RECT *pBorders )
{
    // Frame that the system gives to a window with these styles, at the DPI
    // of the window when the system can tell it (Windows 10 1607)
    typedef UINT (WINAPI *GetDpiForWindow_t)( HWND );
    typedef BOOL (WINAPI *AdjustWindowRectExForDpi_t)( LPRECT, DWORD, BOOL,
                                                      DWORD, UINT );
    static HMODULE hUser32 = GetModuleHandle( TEXT("user32.dll") );
    static GetDpiForWindow_t pGetDpiForWindow = (GetDpiForWindow_t)(void*)
        GetProcAddress( hUser32, "GetDpiForWindow" );
    static AdjustWindowRectExForDpi_t pAdjustForDpi =
        (AdjustWindowRectExForDpi_t)(void*)
        GetProcAddress( hUser32, "AdjustWindowRectExForDpi" );

    DWORD style = (DWORD)GetWindowLongPtr( hWnd, GWL_STYLE ) &
                  ~( WS_MAXIMIZE | WS_MINIMIZE );
    DWORD exStyle = (DWORD)GetWindowLongPtr( hWnd, GWL_EXSTYLE );
    RECT frame = { 0, 0, 0, 0 };
    if( !pGetDpiForWindow || !pAdjustForDpi ||
        !pAdjustForDpi( &frame, style, FALSE, exStyle,
                        pGetDpiForWindow( hWnd ) ) )
    {
        SetRectEmpty( &frame );
        AdjustWindowRectEx( &frame, style, FALSE, exStyle );
    }

    pBorders->left = -frame.left;
    pBorders->top = 0;
    pBorders->right = frame.right;
    pBorders->bottom = frame.bottom;
}


void Win32Window::moveResize( int left, int top, int width, int height ) const
{
    if( m_snappable )
    {
        // The skin gives the area that it draws: the sizing borders of the
        // window lie around it
        RECT borders;
        getSizingBorders( m_hWnd, &borders );
        left -= borders.left;
        width += borders.left + borders.right;
        height += borders.bottom;

        // Nothing to do when the window is there already: the usual case
        // when the system resizes it and the skin follows. MoveWindow would
        // repaint it at once, before the layout is drawn at the new size.
        RECT rc;
        if( GetWindowRect( m_hWnd, &rc ) && rc.left == left &&
            rc.top == top && rc.right - rc.left == width &&
            rc.bottom - rc.top == height )
            return;
    }

    // Mark this as a plugin-initiated geometry change: the WM_WINDOWPOSCHANGED
    // that MoveWindow sends synchronously must not be echoed back as if the
    // user had snapped or dragged the window.
    m_selfMove++;
    MoveWindow( m_hWnd, left, top, width, height, TRUE );
    m_selfMove--;
}""")])

patch("win32/win32_graphics.cpp", [(
"""    HRGN mask = CreateRectRgn( 0, 0, 0, 0 );
    CombineRgn( mask, m_mask, NULL, RGN_COPY );
    SetWindowRgn( hWnd, mask, TRUE );""",
"""    HRGN mask = CreateRectRgn( 0, 0, 0, 0 );
    CombineRgn( mask, m_mask, NULL, RGN_COPY );
    if( rWin.isSnappable() )
    {
        // The region is relative to the window, the mask to the area drawn
        // by the skin, which begins after the left sizing border
        RECT borders;
        Win32Window::getSizingBorders( hWnd, &borders );
        OffsetRgn( mask, borders.left, borders.top );
    }
    SetWindowRgn( hWnd, mask, TRUE );""")])

patch("win32/win32_loop.cpp", [(
"""#include "win32_loop.hpp"
#include "../src/generic_window.hpp"
""",
"""#include "win32_loop.hpp"
#include "win32_window.hpp"
#include "../src/generic_window.hpp"
#include "../src/window_manager.hpp"
"""), (
"""                RECT rc;
                if( GetWindowRect( hwnd, &rc ) )
                    win.onOSGeometryChange( rc.left, rc.top,
                                            rc.right - rc.left,
                                            rc.bottom - rc.top,
                                            IsZoomed( hwnd ) != 0 );""",
"""                // The skin is the client area: the sizing borders of the
                // window lie around it
                RECT rc;
                POINT origin = { 0, 0 };
                if( GetClientRect( hwnd, &rc ) &&
                    ClientToScreen( hwnd, &origin ) )
                    win.onOSGeometryChange( origin.x, origin.y,
                                            rc.right, rc.bottom,
                                            IsZoomed( hwnd ) != 0 );"""), (
"""            // The sizing frame only exists to make the window snappable:
            // no non-client area, the skin draws the whole window
            if( win.isSnappable() )
                return 0;
            break;""",
"""            // No caption and no border at the top: the skin draws the whole
            // visible window. The sizing borders of the frame are kept on
            // the other sides: the system leaves them invisible and they are
            // the area, just outside of the window, that it is resized from,
            // as for any window of Windows 10 and 11. With wParam TRUE,
            // returning 0 keeps the content aligned with the top left corner.
            if( win.isSnappable() )
            {
                // lParam: a RECT, or a NCCALCSIZE_PARAMS that begins with it
                RECT *pRect = (RECT*)lParam;
                RECT borders;
                Win32Window::getSizingBorders( hwnd, &borders );
                pRect->left += borders.left;
                pRect->right -= borders.right;
                pRect->bottom -= borders.bottom;
                if( pRect->right < pRect->left )
                    pRect->right = pRect->left;
                if( pRect->bottom < pRect->top )
                    pRect->bottom = pRect->top;
                return 0;
            }
            break;"""), (
"""            // No system borders or caption: the skin handles move and resize
            if( win.isSnappable() )
                return HTCLIENT;
            break;""",
"""            // A window that draws its own frame has to give back the
            // standard resizing through this message: the system then does
            // the resizing itself, from every side.
            if( !win.isSnappable() )
                break;

            // The sizing borders around the window (left, right, bottom)
            LRESULT hit = DefWindowProc( hwnd, msg, wParam, lParam );
            bool inClient = ( hit == HTCLIENT );

            // Directions in which the active layout can be resized
            int minWidth, minHeight, maxWidth, maxHeight;
            bool sizable = !IsZoomed( hwnd ) &&
                win.getSizeLimits( &minWidth, &minHeight,
                                   &maxWidth, &maxHeight );
            bool horizontal = sizable && maxWidth > minWidth;
            bool vertical = sizable && maxHeight > minHeight;

            if( inClient )
            {
                POINT pt = { GET_X_LPARAM( lParam ), GET_Y_LPARAM( lParam ) };
                RECT rc, borders;
                ScreenToClient( hwnd, &pt );
                GetClientRect( hwnd, &rc );
                Win32Window::getSizingBorders( hwnd, &borders );
                int band = borders.bottom;
                if( vertical && pt.y < band )
                {
                    // There is no border at the top: its sizing area is the
                    // top edge of the skin, as in the applications that draw
                    // their own title bar
                    if( pt.x < 2 * band )
                        hit = HTTOPLEFT;
                    else if( pt.x >= rc.right - 2 * band )
                        hit = HTTOPRIGHT;
                    else
                        hit = HTTOP;
                }
                else
                {
                    // Resize handles drawn by the skin: same resizing
                    switch( win.getResizeHandle( pt.x, pt.y ) )
                    {
                    case WindowManager::kResizeE:
                        hit = HTRIGHT;
                        break;
                    case WindowManager::kResizeS:
                        hit = HTBOTTOM;
                        break;
                    case WindowManager::kResizeSE:
                        hit = HTBOTTOMRIGHT;
                        break;
                    default:
                        break;
                    }
                }
            }

            // Only the directions that the layout allows
            bool left = ( hit == HTLEFT || hit == HTTOPLEFT ||
                          hit == HTBOTTOMLEFT );
            bool right = ( hit == HTRIGHT || hit == HTTOPRIGHT ||
                           hit == HTBOTTOMRIGHT );
            bool top = ( hit == HTTOP || hit == HTTOPLEFT ||
                         hit == HTTOPRIGHT );
            bool bottom = ( hit == HTBOTTOM || hit == HTBOTTOMLEFT ||
                            hit == HTBOTTOMRIGHT );
            if( left || right || top || bottom )
            {
                bool h = ( left || right ) && horizontal;
                bool v = ( top || bottom ) && vertical;
                if( h && !v )
                    hit = left ? HTLEFT : HTRIGHT;
                else if( v && !h )
                    hit = top ? HTTOP : HTBOTTOM;
                else if( !h && !v )
                    hit = inClient ? HTCLIENT : HTBORDER;
            }
            return hit;"""), (
"""            // Maximize exactly to the work area of the current monitor
            if( win.isSnappable() )
            {
                HMONITOR hMon = MonitorFromWindow( hwnd,
                                                   MONITOR_DEFAULTTONEAREST );
                MONITORINFO mi;
                mi.cbSize = sizeof( mi );
                if( hMon && GetMonitorInfo( hMon, &mi ) )
                {
                    MINMAXINFO *pInfo = (MINMAXINFO*)lParam;
                    pInfo->ptMaxPosition.x = mi.rcWork.left - mi.rcMonitor.left;
                    pInfo->ptMaxPosition.y = mi.rcWork.top - mi.rcMonitor.top;
                    pInfo->ptMaxSize.x = mi.rcWork.right - mi.rcWork.left;
                    pInfo->ptMaxSize.y = mi.rcWork.bottom - mi.rcWork.top;
                    return 0;
                }
            }
            break;""",
"""            if( win.isSnappable() )
            {
                MINMAXINFO *pInfo = (MINMAXINFO*)lParam;
                RECT borders;
                Win32Window::getSizingBorders( hwnd, &borders );
                int extraWidth = borders.left + borders.right;
                int extraHeight = borders.bottom;

                // Sizes that the borders can give to the window: the limits
                // of the active layout. The system also honours them when it
                // arranges the window (Snap).
                int minWidth, minHeight, maxWidth, maxHeight;
                if( win.getSizeLimits( &minWidth, &minHeight,
                                       &maxWidth, &maxHeight ) )
                {
                    pInfo->ptMinTrackSize.x = minWidth + extraWidth;
                    pInfo->ptMinTrackSize.y = minHeight + extraHeight;
                    if( maxWidth + extraWidth < pInfo->ptMaxTrackSize.x )
                        pInfo->ptMaxTrackSize.x = maxWidth + extraWidth;
                    if( maxHeight + extraHeight < pInfo->ptMaxTrackSize.y )
                        pInfo->ptMaxTrackSize.y = maxHeight + extraHeight;
                }

                // Maximized, the skin covers exactly the work area of the
                // current monitor; the sizing borders lie outside of it
                HMONITOR hMon = MonitorFromWindow( hwnd,
                                                   MONITOR_DEFAULTTONEAREST );
                MONITORINFO mi;
                mi.cbSize = sizeof( mi );
                if( hMon && GetMonitorInfo( hMon, &mi ) )
                {
                    pInfo->ptMaxPosition.x = mi.rcWork.left - mi.rcMonitor.left -
                                             borders.left;
                    pInfo->ptMaxPosition.y = mi.rcWork.top - mi.rcMonitor.top;
                    pInfo->ptMaxSize.x = mi.rcWork.right - mi.rcWork.left +
                                         extraWidth;
                    pInfo->ptMaxSize.y = mi.rcWork.bottom - mi.rcWork.top +
                                         extraHeight;
                }
                return 0;
            }
            break;""")])

# ------------------------------------------------------------------ sfondo nero per la finestra che ospita il video
# La finestra che ospita il video (figlia della finestra della skin) non viene mai dipinta: alla skin i suoi messaggi
# non arrivano nemmeno (Win32Proc li passa a DefWindowProc, perche' il puntatore all'interfaccia viene salvato solo
# nelle finestre di primo livello) e la classe non ha un pennello di sfondo. La copre l'uscita video di VLC, che pero'
# vive in un altro thread e segue un ridimensionamento qualche fotogramma dopo. Nel frattempo la parte non ancora
# coperta mostrava quel che la superficie della finestra aveva prima in quel punto: allargando, una striscia chiara
# lungo il video (la cornice di ridimensionamento come la dipinge il sistema: Windows non la mostra, ma nella
# superficie c'e'); allungando verso il basso, un'ombra della barra dei comandi.
# Ora quella finestra ha lo sfondo nero, come le bande attorno all'immagine.
patch("win32/win32_factory.cpp", [(
"""    // If doesn't exist, treat windows message normally
    if( p_intf == NULL || p_intf->p_sys->p_osFactory == NULL )
    {
        return DefWindowProc( hwnd, uMsg, wParam, lParam );
    }
""",
"""    // If doesn't exist, treat windows message normally
    if( p_intf == NULL || p_intf->p_sys->p_osFactory == NULL )
    {
        // The window that hosts the video (the only child window of this
        // class) ends up here. Nobody paints it: the video output covers
        // it, but from another thread, some frames after a resize. What
        // is not covered yet must be black, like the bars around the
        // picture, and not what the surface of the window held there
        // before (a light strip along the video while the window is being
        // enlarged, a ghost of the control bar while it is made taller).
        if( uMsg == WM_ERASEBKGND &&
            ( GetWindowLongPtr( hwnd, GWL_STYLE ) & WS_CHILD ) )
        {
            RECT rc;
            GetClientRect( hwnd, &rc );
            FillRect( (HDC)wParam, &rc,
                      (HBRUSH)GetStockObject( BLACK_BRUSH ) );
            return 1;
        }
        return DefWindowProc( hwnd, uMsg, wParam, lParam );
    }
""")])

# ------------------------------------------------------------------ menu di disposizione sul pulsante Ingrandisci
# Su Windows 11 il menu con i layout di aggancio compare da solo sul pulsante Ingrandisci delle barre del titolo di
# sistema. Una finestra che disegna la propria barra deve dire a Windows dov'e' quel pulsante rispondendo HTMAXBUTTON
# a WM_NCHITTEST ("Support snap layouts for desktop apps on Windows 11", Microsoft Learn). Qui il pulsante e' quello
# della skin: il controllo (pulsante o casella) il cui comando ingrandisce o ripristina la finestra.
# Da quel momento per Windows il pulsante e' "non client" e i messaggi del mouse arrivano in quella forma: il modulo li
# rigira alla skin come eventi normali (passaggio, uscita, clic), cosi' il pulsante resta quello di prima; il clic non
# va a DefWindowProc, che seguirebbe la pressione di un pulsante di sistema che non esiste.
patch("controls/ctrl_generic.hpp", [(
"""    virtual int getResizeDirection() const { return -1; }
""",
"""    virtual int getResizeDirection() const { return -1; }

    /// Return true if the control maximizes or restores its window
    virtual bool isMaximizeButton() const { return false; }
""")])

patch("controls/ctrl_button.hpp", [(
"""    virtual std::string getType() const { return "button"; }
""",
"""    virtual std::string getType() const { return "button"; }

    /// Return true if the button maximizes or restores its window
    virtual bool isMaximizeButton() const;
""")])

patch("controls/ctrl_button.cpp", [(
"""bool CtrlButton::mouseOver( int x, int y ) const
{""",
"""bool CtrlButton::isMaximizeButton() const
{
    std::string type = m_rCommand.getType();
    return type == "maximize" || type == "unmaximize";
}


bool CtrlButton::mouseOver( int x, int y ) const
{""")])

patch("controls/ctrl_checkbox.hpp", [(
"""    virtual std::string getType() const { return "checkbox"; }
""",
"""    virtual std::string getType() const { return "checkbox"; }

    /// Return true if the checkbox maximizes or restores its window
    virtual bool isMaximizeButton() const;
""")])

patch("controls/ctrl_checkbox.cpp", [(
"""bool CtrlCheckbox::mouseOver( int x, int y ) const
{""",
"""bool CtrlCheckbox::isMaximizeButton() const
{
    std::string type1 = m_rCommand1.getType();
    std::string type2 = m_rCommand2.getType();
    return type1 == "maximize" || type1 == "unmaximize" ||
           type2 == "maximize" || type2 == "unmaximize";
}


bool CtrlCheckbox::mouseOver( int x, int y ) const
{""")])

patch("src/generic_window.hpp", [(
"""    virtual int getResizeHandle( int xPos, int yPos ) const
        { (void)xPos; (void)yPos; return -1; }
""",
"""    virtual int getResizeHandle( int xPos, int yPos ) const
        { (void)xPos; (void)yPos; return -1; }

    /// True if the control of the skin at the given position in the window
    /// maximizes or restores it
    virtual bool isMaximizeButtonAt( int xPos, int yPos ) const
        { (void)xPos; (void)yPos; return false; }
""")])

patch("src/top_window.hpp", [(
"""    /// Resize handle of the active layout at the given position
    virtual int getResizeHandle( int xPos, int yPos ) const;
""",
"""    /// Resize handle of the active layout at the given position
    virtual int getResizeHandle( int xPos, int yPos ) const;

    /// True if the maximize / restore button of the active layout is at
    /// the given position
    virtual bool isMaximizeButtonAt( int xPos, int yPos ) const;
"""), (
"""    /// Called by a control that wants to capture the mouse
    virtual void onControlCapture( const CtrlGeneric &rCtrl );
""",
"""    /// Uppermost control of the active layout at the given position, as
    /// findHitControl() finds it, but without telling anything to the
    /// controls; NULL if there is none
    CtrlGeneric *getControlAt( int xPos, int yPos ) const;

    /// Called by a control that wants to capture the mouse
    virtual void onControlCapture( const CtrlGeneric &rCtrl );
""")])

patch_between("src/top_window.cpp", "int TopWindow::getResizeHandle( int xPos, int yPos ) const\n",
"""            return pCtrl->getResizeDirection();
        }
    }
    return -1;
}
""",
"""CtrlGeneric *TopWindow::getControlAt( int xPos, int yPos ) const
{
    if( m_pActiveLayout == NULL )
        return NULL;

    const std::list<LayeredControl> &ctrlList = m_pActiveLayout->getControlList();
    std::list<LayeredControl>::const_reverse_iterator iter;
    for( iter = ctrlList.rbegin(); iter != ctrlList.rend(); ++iter )
    {
        CtrlGeneric *pCtrl = (*iter).m_pControl;
        const Position *pos = pCtrl->getPosition();
        if( pos != NULL && pCtrl->isVisible() &&
            pCtrl->mouseOver( xPos - pos->getLeft(), yPos - pos->getTop() ) )
        {
            return pCtrl;
        }
    }
    return NULL;
}


int TopWindow::getResizeHandle( int xPos, int yPos ) const
{
    CtrlGeneric *pCtrl = getControlAt( xPos, yPos );
    return pCtrl ? pCtrl->getResizeDirection() : -1;
}


bool TopWindow::isMaximizeButtonAt( int xPos, int yPos ) const
{
    CtrlGeneric *pCtrl = getControlAt( xPos, yPos );
    return pCtrl && pCtrl->isMaximizeButton();
}
""")

patch("win32/win32_loop.hpp", [(
"""    /// Helper function to find the modifier in a Windows message
    int getMod( WPARAM wParam ) const;
""",
"""    /// Helper function to find the modifier in a Windows message
    int getMod( WPARAM wParam ) const;

    /// Window whose maximize button (non client area for the system) has
    /// the mouse over it, NULL if none
    HWND m_hMaxButtonHover;
""")])

patch("win32/win32_loop.cpp", [(
"""Win32Loop::Win32Loop( intf_thread_t *pIntf ): OSLoop( pIntf )
{""",
"""Win32Loop::Win32Loop( intf_thread_t *pIntf ): OSLoop( pIntf ),
    m_hMaxButtonHover( NULL )
{"""), (
"""                else
                {
                    // Resize handles drawn by the skin: same resizing
                    switch( win.getResizeHandle( pt.x, pt.y ) )""",
"""                else if( win.isMaximizeButtonAt( pt.x, pt.y ) )
                {
                    // The maximize button of the skin: on Windows 11 the
                    // system shows the snap layouts menu over it
                    hit = HTMAXBUTTON;
                }
                else
                {
                    // Resize handles drawn by the skin: same resizing
                    switch( win.getResizeHandle( pt.x, pt.y ) )"""), (
"""        case WM_GETMINMAXINFO:
        {""",
"""        case WM_NCMOUSEMOVE:
        {
            // The maximize button of the skin is non client area for the
            // system (see WM_NCHITTEST) and a control like the others for
            // the skin, which gets the mouse events that no longer come as
            // client messages. The message goes on to DefWindowProc.
            if( !win.isSnappable() )
                break;
            if( wParam == HTMAXBUTTON )
            {
                TRACKMOUSEEVENT TrackEvent;
                TrackEvent.cbSize      = sizeof( TRACKMOUSEEVENT );
                TrackEvent.dwFlags     = TME_LEAVE | TME_NONCLIENT;
                TrackEvent.hwndTrack   = hwnd;
                TrackEvent.dwHoverTime = 1;
                TrackMouseEvent( &TrackEvent );
                m_hMaxButtonHover = hwnd;

                // screen coordinates, as the motion events want them
                EvtMotion evt( getIntf(), GET_X_LPARAM( lParam ),
                               GET_Y_LPARAM( lParam ) );
                win.processEvent( evt );
            }
            else if( m_hMaxButtonHover == hwnd )
            {
                // from the button to another part of the non client area
                m_hMaxButtonHover = NULL;
                EvtLeave evt( getIntf() );
                win.processEvent( evt );
            }
            break;
        }
        case WM_NCMOUSELEAVE:
        {
            if( m_hMaxButtonHover == hwnd )
            {
                m_hMaxButtonHover = NULL;
                EvtLeave evt( getIntf() );
                win.processEvent( evt );
            }
            break;
        }
        case WM_NCLBUTTONDOWN:
        case WM_NCLBUTTONDBLCLK:
        case WM_NCLBUTTONUP:
        {
            // A click on the maximize button of the skin: for the skin, not
            // for DefWindowProc, which would track the press of a caption
            // button that does not exist. Once the mouse is captured, the
            // release comes as a client message.
            if( win.isSnappable() && wParam == HTMAXBUTTON )
            {
                POINT pt = { GET_X_LPARAM( lParam ), GET_Y_LPARAM( lParam ) };
                ScreenToClient( hwnd, &pt );
                EvtMouse::ActionType_t action = EvtMouse::kUp;
                if( msg == WM_NCLBUTTONDOWN )
                {
                    SetCapture( hwnd );
                    action = EvtMouse::kDown;
                }
                else
                {
                    ReleaseCapture();
                    if( msg == WM_NCLBUTTONDBLCLK )
                        action = EvtMouse::kDblClick;
                }
                EvtMouse evt( getIntf(), pt.x, pt.y, EvtMouse::kLeft, action );
                win.processEvent( evt );
                return 0;
            }
            break;
        }
        case WM_GETMINMAXINFO:
        {""")])

# ------------------------------------------------------------------ comando della skin per aprire una pagina web
# vlc.openLink(indirizzo) apre nel browser predefinito un indirizzo http o https scritto nella skin: serve alla voce
# "Offrimi un caffe'" del menu di Aurora. Solo indirizzi web: ShellExecute, con altro, avvierebbe qualunque cosa.
patch("commands/cmd_minimize.hpp", [(
"""/// Command to open the page of the HTTP interface in the default browser
DEFINE_COMMAND( WebInterface,      "web interface" )
""",
"""/// Command to open the page of the HTTP interface in the default browser
DEFINE_COMMAND( WebInterface,      "web interface" )

/// Command to open a web page (http or https address) in the default browser
class CmdOpenLink: public CmdGeneric
{
public:
    CmdOpenLink( intf_thread_t *pIntf, const std::string &rUrl ):
        CmdGeneric( pIntf ), m_url( rUrl ) { }
    virtual ~CmdOpenLink() { }
    virtual void execute();
    virtual std::string getType() const { return "open link"; }

private:
    /// Address of the page
    std::string m_url;
};
""")])

patch("commands/cmd_minimize.cpp", [(
"""void CmdWebInterface::execute()
{""",
"""void CmdOpenLink::execute()
{
#ifdef _WIN32
    // Web addresses only: ShellExecute would run anything else
    if( m_url.compare( 0, 8, "https://" ) != 0 &&
        m_url.compare( 0, 7, "http://" ) != 0 )
    {
        msg_Warn( getIntf(), "not a web address: %s", m_url.c_str() );
        return;
    }
    INT_PTR ret = (INT_PTR)ShellExecuteA( NULL, "open", m_url.c_str(), NULL,
                                          NULL, SW_SHOWNORMAL );
    if( ret > 32 )
        msg_Dbg( getIntf(), "link opened in the browser: %s", m_url.c_str() );
    else
        msg_Warn( getIntf(), "cannot open %s (error %d)", m_url.c_str(),
                  (int)ret );
#else
    msg_Warn( getIntf(), "opening a link is not supported here" );
#endif
}


void CmdWebInterface::execute()
{""")])

patch("parser/interpreter.cpp", [(
"""    else if( rAction.find( ".setLayout(" ) != std::string::npos )
    {
        int leftPos = rAction.find( ".setLayout(" );""",
"""    else if( rAction.compare( 0, 13, "vlc.openLink(" ) == 0 &&
             rAction[rAction.size() - 1] == ')' )
    {
        // 13 is the size of "vlc.openLink("
        pCommand = new CmdOpenLink( getIntf(),
                                    rAction.substr( 13, rAction.size() - 14 ) );
    }
    else if( rAction.find( ".setLayout(" ) != std::string::npos )
    {
        int leftPos = rAction.find( ".setLayout(" );""")])

# ------------------------------------------------------------------ nota nei file modificati
# La GPL (versione 2, articolo 2a) chiede che i file modificati lo dicano, con la data. La nota va nella seconda riga
# dell'intestazione di ogni file toccato, quella con il nome del file: cosi' non si aggiungono righe.
NOTA = " (modified in 2026 for the VLC Aurora kit: see plugin/LEGGIMI.txt)"
LF, CR = chr(10), chr(13)
for rel in sorted(MODIFICATI):
    p = os.path.join(DST, rel)
    righe = open(p, encoding="utf-8", newline="").read().split(LF)
    if len(righe) > 1 and righe[0].startswith("/*") and righe[1].startswith(" * "):
        coda = CR if righe[1].endswith(CR) else ""
        righe[1] = righe[1].rstrip(CR) + NOTA + coda
    else:
        righe.insert(0, "/*" + NOTA + " */")
    open(p, "w", encoding="utf-8", newline="").write(LF.join(righe))
print("nota di modifica in", len(MODIFICATI), "file")

print("patch applicata in", DST)
