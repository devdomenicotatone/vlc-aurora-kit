/*****************************************************************************
 * win32_window.cpp (modified in 2026 for the VLC Aurora kit: see plugin/LEGGIMI.txt)
 *****************************************************************************
 * Copyright (C) 2003 the VideoLAN team
 * $Id$
 *
 * Authors: Cyril Deguet     <asmax@via.ecp.fr>
 *          Olivier Teulière <ipkiss@via.ecp.fr>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston MA 02110-1301, USA.
 *****************************************************************************/

#ifdef WIN32_SKINS

#include "../src/generic_window.hpp"
#include "../src/vlcproc.hpp"
#include "../src/vout_manager.hpp"
#include "win32_window.hpp"
#include "win32_dragdrop.hpp"
#include "win32_factory.hpp"
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


/// Fading API
#ifndef LWA_COLORKEY
#   define LWA_COLORKEY  0x00000001
#   define LWA_ALPHA     0x00000002
#endif


// XXX layered windows are supposed to work only with at least win2k
#ifndef WS_EX_LAYERED
#   define WS_EX_LAYERED 0x00080000
#endif

Win32Window::Win32Window( intf_thread_t *pIntf, GenericWindow &rWindow,
                          HINSTANCE hInst, HWND hParentWindow,
                          bool dragDrop, bool playOnDrop,
                          Win32Window *pParentWindow,
                          GenericWindow::WindowType_t type ):
    OSWindow( pIntf ), m_dragDrop( dragDrop ), m_isLayered( false ),
    m_pParent( pParentWindow ), m_type ( type ), m_snappable( false ),
    m_selfMove( 0 ), m_hasRegion( false ), m_borderColor( CLR_INVALID )
{
    (void)hParentWindow;
    Win32Factory *pFactory = (Win32Factory*)Win32Factory::instance( getIntf() );

    LPCTSTR vlc_name =  TEXT("VlC Media Player");
    LPCTSTR vlc_class = TEXT("SkinWindowClass");

    // Create the window
    if( type == GenericWindow::VoutWindow )
    {
        // Child window (for vout)
        m_hWnd_parent = pParentWindow->getHandle();
        m_hWnd = CreateWindowEx( WS_EX_TOOLWINDOW | WS_EX_NOPARENTNOTIFY,
                     vlc_class, vlc_name,
                     WS_CHILD | WS_CLIPCHILDREN | WS_CLIPSIBLINGS,
                     0, 0, 0, 0, m_hWnd_parent, 0, hInst, NULL );
    }
    else if( type == GenericWindow::FullscreenWindow )
    {
        // top-level window
        m_hWnd = CreateWindowEx( WS_EX_APPWINDOW, vlc_class,
                                 vlc_name, WS_POPUP | WS_CLIPCHILDREN,
                                 0, 0, 0, 0, NULL, 0, hInst, NULL );

        // Store with it a pointer to the interface thread
        SetWindowLongPtr( m_hWnd, GWLP_USERDATA, (LONG_PTR)getIntf() );
    }
    else if( type == GenericWindow::FscWindow )
    {
        VoutManager* pVoutManager = VoutManager::instance( getIntf() );
        GenericWindow* pParent =
           (GenericWindow*)pVoutManager->getVoutMainWindow();

        m_hWnd_parent = (HWND)pParent->getOSHandle();

        // top-level window
        m_hWnd = CreateWindowEx( WS_EX_APPWINDOW, vlc_class, vlc_name,
                                 WS_POPUP | WS_CLIPCHILDREN | WS_CLIPSIBLINGS,
                                 0, 0, 0, 0, m_hWnd_parent, 0, hInst, NULL );

        // Store with it a pointer to the interface thread
        SetWindowLongPtr( m_hWnd, GWLP_USERDATA, (LONG_PTR)getIntf() );
    }
    else
    {
        // top-level window (owned by the root window).
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

        // Store with it a pointer to the interface thread
        SetWindowLongPtr( m_hWnd, GWLP_USERDATA, (LONG_PTR)getIntf() );
    }

    if( !m_hWnd )
    {
        msg_Err( getIntf(), "CreateWindow failed" );
        return;
    }

    // Store a pointer to the GenericWindow in a map
    pFactory->m_windowMap[m_hWnd] = &rWindow;

    // Drag & drop
    if( m_dragDrop )
    {
        m_pDropTarget = (LPDROPTARGET)
            new Win32DragDrop( getIntf(), playOnDrop, &rWindow );
        // Register the window as a drop target
        RegisterDragDrop( m_hWnd, m_pDropTarget );
    }
}


Win32Window::~Win32Window()
{
    Win32Factory *pFactory = (Win32Factory*)Win32Factory::instance( getIntf() );
    pFactory->m_windowMap[m_hWnd] = NULL;

    if( m_hWnd )
    {
        if( m_dragDrop )
        {
            // Remove the window from the list of drop targets
            RevokeDragDrop( m_hWnd );
            m_pDropTarget->Release();
        }

        DestroyWindow( m_hWnd );
    }
}


void Win32Window::reparent( void* OSHandle, int x, int y, int w, int h )
{
    // Reparent the window
    if( !SetParent( m_hWnd, (HWND)OSHandle ) )
        msg_Err( getIntf(), "SetParent failed (%lu)", GetLastError() );
    MoveWindow( m_hWnd, x, y, w, h, TRUE );
}


bool Win32Window::invalidateRect( int x, int y, int w, int h) const
{
    RECT rect = { x, y, x + w , y + h };
    InvalidateRect( m_hWnd, &rect, FALSE );
    UpdateWindow( m_hWnd );

    return true;
}


void Win32Window::show() const
{

    if( m_type == GenericWindow::VoutWindow )
    {
        SetWindowPos( m_hWnd, HWND_BOTTOM, 0, 0, 0, 0,
                              SWP_NOMOVE | SWP_NOSIZE );
    }
    else if( m_type == GenericWindow::FullscreenWindow )
    {
        SetWindowPos( m_hWnd, HWND_TOPMOST, 0, 0, 0, 0,
                              SWP_NOMOVE | SWP_NOSIZE );
    }

    ShowWindow( m_hWnd, SW_SHOW );
}


void Win32Window::hide() const
{
    ShowWindow( m_hWnd, SW_HIDE );
}


void Win32Window::getSizingBorders( HWND hWnd, RECT *pBorders )
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
}


void Win32Window::raise() const
{
//     SetWindowPos( m_hWnd, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE );
    SetForegroundWindow( m_hWnd );
}


void Win32Window::setOpacity( uint8_t value ) const
{
    if( !m_isLayered )
    {
        // add the WS_EX_LAYERED attribute.
        SetWindowLongPtr( m_hWnd, GWL_EXSTYLE,
            GetWindowLongPtr( m_hWnd, GWL_EXSTYLE ) | WS_EX_LAYERED );

        m_isLayered = true;
    }

    // Change the opacity
    SetLayeredWindowAttributes( m_hWnd, 0, value, LWA_ALPHA );
}


void Win32Window::toggleOnTop( bool onTop ) const
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


#endif
