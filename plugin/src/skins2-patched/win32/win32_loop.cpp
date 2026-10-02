/*****************************************************************************
 * win32_loop.cpp (modified in 2026 for the VLC Aurora kit: see plugin/LEGGIMI.txt)
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

#include "win32_factory.hpp"
#include "win32_loop.hpp"
#include "win32_window.hpp"
#include "../src/generic_window.hpp"
#include "../src/window_manager.hpp"
#include "../events/evt_key.hpp"
#include "../events/evt_leave.hpp"
#include "../events/evt_menu.hpp"
#include "../events/evt_motion.hpp"
#include "../events/evt_mouse.hpp"
#include "../events/evt_refresh.hpp"
#include "../events/evt_scroll.hpp"
#include <vlc_actions.h>


// XXX: Cygwin (at least) doesn't define these macros. Too bad...
#ifndef GET_X_LPARAM
    #define GET_X_LPARAM(a) ((int16_t)(a))
    #define GET_Y_LPARAM(a) ((int16_t)((a)>>16))
#endif


Win32Loop::Win32Loop( intf_thread_t *pIntf ): OSLoop( pIntf ),
    m_hMaxButtonHover( NULL )
{
    // Initialize the map
    virtKeyToVlcKey[VK_F1] = KEY_F1;
    virtKeyToVlcKey[VK_F2] = KEY_F2;
    virtKeyToVlcKey[VK_F3] = KEY_F3;
    virtKeyToVlcKey[VK_F4] = KEY_F4;
    virtKeyToVlcKey[VK_F5] = KEY_F5;
    virtKeyToVlcKey[VK_F6] = KEY_F6;
    virtKeyToVlcKey[VK_F7] = KEY_F7;
    virtKeyToVlcKey[VK_F8] = KEY_F8;
    virtKeyToVlcKey[VK_F9] = KEY_F9;
    virtKeyToVlcKey[VK_F10] = KEY_F10;
    virtKeyToVlcKey[VK_F11] = KEY_F11;
    virtKeyToVlcKey[VK_F12] = KEY_F12;
    virtKeyToVlcKey[VK_RETURN] = KEY_ENTER;
    virtKeyToVlcKey[VK_SPACE] = ' ';
    virtKeyToVlcKey[VK_ESCAPE] = KEY_ESC;
    virtKeyToVlcKey[VK_LEFT] = KEY_LEFT;
    virtKeyToVlcKey[VK_RIGHT] = KEY_RIGHT;
    virtKeyToVlcKey[VK_UP] = KEY_UP;
    virtKeyToVlcKey[VK_DOWN] = KEY_DOWN;
    virtKeyToVlcKey[VK_INSERT] = KEY_INSERT;
    virtKeyToVlcKey[VK_DELETE] = KEY_DELETE;
    virtKeyToVlcKey[VK_HOME] = KEY_HOME;
    virtKeyToVlcKey[VK_END] = KEY_END;
    virtKeyToVlcKey[VK_PRIOR] = KEY_PAGEUP;
    virtKeyToVlcKey[VK_NEXT] = KEY_PAGEDOWN;
    virtKeyToVlcKey[VK_BROWSER_BACK] = KEY_BROWSER_BACK;
    virtKeyToVlcKey[VK_BROWSER_FORWARD] = KEY_BROWSER_FORWARD;
    virtKeyToVlcKey[VK_BROWSER_REFRESH] = KEY_BROWSER_REFRESH;
    virtKeyToVlcKey[VK_BROWSER_STOP] = KEY_BROWSER_STOP;
    virtKeyToVlcKey[VK_BROWSER_SEARCH] = KEY_BROWSER_SEARCH;
    virtKeyToVlcKey[VK_BROWSER_FAVORITES] = KEY_BROWSER_FAVORITES;
    virtKeyToVlcKey[VK_BROWSER_HOME] = KEY_BROWSER_HOME;
    virtKeyToVlcKey[VK_VOLUME_MUTE] = KEY_VOLUME_MUTE;
    virtKeyToVlcKey[VK_VOLUME_DOWN] = KEY_VOLUME_DOWN;
    virtKeyToVlcKey[VK_VOLUME_UP] = KEY_VOLUME_UP;
    virtKeyToVlcKey[VK_MEDIA_NEXT_TRACK] = KEY_MEDIA_NEXT_TRACK;
    virtKeyToVlcKey[VK_MEDIA_PREV_TRACK] = KEY_MEDIA_PREV_TRACK;
    virtKeyToVlcKey[VK_MEDIA_STOP] = KEY_MEDIA_STOP;
    virtKeyToVlcKey[VK_MEDIA_PLAY_PAUSE] = KEY_MEDIA_PLAY_PAUSE;
}


Win32Loop::~Win32Loop()
{
}


OSLoop *Win32Loop::instance( intf_thread_t *pIntf )
{
    if( pIntf->p_sys->p_osLoop == NULL )
    {
        OSLoop *pOsLoop = new Win32Loop( pIntf );
        pIntf->p_sys->p_osLoop = pOsLoop;
    }
    return pIntf->p_sys->p_osLoop;
}


void Win32Loop::destroy( intf_thread_t *pIntf )
{
    delete pIntf->p_sys->p_osLoop;
    pIntf->p_sys->p_osLoop = NULL;
}


void Win32Loop::run()
{
    MSG msg;

    // Compute windows message list
    while( GetMessage( &msg, NULL, 0, 0 ) )
    {
        TranslateMessage( &msg );
        DispatchMessage( &msg );
    }
}


LRESULT CALLBACK Win32Loop::processEvent( HWND hwnd, UINT msg,
                                          WPARAM wParam, LPARAM lParam )
{
    Win32Factory *pFactory =
        (Win32Factory*)Win32Factory::instance( getIntf() );
    GenericWindow *pWin = pFactory->m_windowMap[hwnd];

    GenericWindow &win = *pWin;
    switch( msg )
    {
        case WM_PAINT:
        {
            PAINTSTRUCT Infos;
            BeginPaint( hwnd, &Infos );
            EvtRefresh evt( getIntf(),
                            Infos.rcPaint.left,
                            Infos.rcPaint.top,
                            Infos.rcPaint.right - Infos.rcPaint.left + 1,
                            Infos.rcPaint.bottom - Infos.rcPaint.top + 1 );
            win.processEvent( evt );
            EndPaint( hwnd, &Infos );
            return 0;
        }
        case WM_COMMAND:
        {
            EvtMenu evt( getIntf(), LOWORD( wParam ) );
            win.processEvent( evt );
            return 0;
        }
        case WM_MOUSEMOVE:
        {
            // Needed to generate WM_MOUSELEAVE events
            TRACKMOUSEEVENT TrackEvent;
            TrackEvent.cbSize      = sizeof( TRACKMOUSEEVENT );
            TrackEvent.dwFlags     = TME_LEAVE;
            TrackEvent.hwndTrack   = hwnd;
            TrackEvent.dwHoverTime = 1;
            TrackMouseEvent( &TrackEvent );

            // Compute the absolute position of the mouse
            int x = GET_X_LPARAM( lParam ) + win.getLeft();
            int y = GET_Y_LPARAM( lParam ) + win.getTop();
            EvtMotion evt( getIntf(), x, y );
            win.processEvent( evt );
            return 0;
        }
        case WM_MOUSELEAVE:
        {
            EvtLeave evt( getIntf() );
            win.processEvent( evt );
            return 0;
        }
        case WM_MOUSEWHEEL:
        {
            int x = GET_X_LPARAM( lParam ) - win.getLeft();
            int y = GET_Y_LPARAM( lParam ) - win.getTop();
            int mod = getMod( wParam );
            if( GET_WHEEL_DELTA_WPARAM( wParam ) > 0 )
            {
                EvtScroll evt( getIntf(), x, y, EvtScroll::kUp, mod );
                win.processEvent( evt );
            }
            else
            {
                EvtScroll evt( getIntf(), x, y, EvtScroll::kDown, mod );
                win.processEvent( evt );
            }
            return 0;
        }
        case WM_LBUTTONDOWN:
        {
            SetCapture( hwnd );
            EvtMouse evt( getIntf(), GET_X_LPARAM( lParam ),
                          GET_Y_LPARAM( lParam ), EvtMouse::kLeft,
                          EvtMouse::kDown, getMod( wParam ) );
            win.processEvent( evt );
            return 0;
        }
        case WM_RBUTTONDOWN:
        {
            SetCapture( hwnd );
            EvtMouse evt( getIntf(), GET_X_LPARAM( lParam ),
                          GET_Y_LPARAM( lParam ), EvtMouse::kRight,
                          EvtMouse::kDown, getMod( wParam ) );
            win.processEvent( evt );
            return 0;
        }
        case WM_LBUTTONUP:
        {
            ReleaseCapture();
            EvtMouse evt( getIntf(), GET_X_LPARAM( lParam ),
                          GET_Y_LPARAM( lParam ), EvtMouse::kLeft,
                          EvtMouse::kUp, getMod( wParam ) );
            win.processEvent( evt );
            return 0;
        }
        case WM_RBUTTONUP:
        {
            ReleaseCapture();
            EvtMouse evt( getIntf(), GET_X_LPARAM( lParam ),
                          GET_Y_LPARAM( lParam ), EvtMouse::kRight,
                          EvtMouse::kUp, getMod( wParam ) );
            win.processEvent( evt );
            return 0;
        }
        case WM_LBUTTONDBLCLK:
        {
            ReleaseCapture();
            EvtMouse evt( getIntf(), GET_X_LPARAM( lParam ),
                          GET_Y_LPARAM( lParam ), EvtMouse::kLeft,
                          EvtMouse::kDblClick, getMod( wParam ) );
            win.processEvent( evt );
            return 0;
        }
        case WM_RBUTTONDBLCLK:
        {
            ReleaseCapture();
            EvtMouse evt( getIntf(), GET_X_LPARAM( lParam ),
                          GET_Y_LPARAM( lParam ), EvtMouse::kRight,
                          EvtMouse::kDblClick, getMod( wParam ) );
            win.processEvent( evt );
            return 0;
        }
        case WM_KEYDOWN:
        case WM_SYSKEYDOWN:
        case WM_KEYUP:
        case WM_SYSKEYUP:
        {
            // The key events are first processed here and not translated
            // into WM_CHAR events because we need to know the status of
            // the modifier keys.

            // Get VLC key code from the virtual key code
            int key = virtKeyToVlcKey[wParam];
            if( !key )
            {
                // This appears to be a "normal" (ascii) key
                key = tolower( (unsigned char)MapVirtualKey( wParam, 2 ) );
            }

            if( key )
            {
                // Get the modifier
                int mod = 0;
                if( GetKeyState( VK_CONTROL ) & 0x8000 )
                {
                    mod |= EvtInput::kModCtrl;
                }
                if( GetKeyState( VK_SHIFT ) & 0x8000 )
                {
                    mod |= EvtInput::kModShift;
                }
                if( GetKeyState( VK_MENU ) & 0x8000 )
                {
                    mod |= EvtInput::kModAlt;
                }

                // Get the state
                EvtKey::ActionType_t state;
                if( msg == WM_KEYDOWN ||
                    msg == WM_SYSKEYDOWN )
                {
                    state = EvtKey::kDown;
                }
                else
                {
                    state = EvtKey::kUp;
                }

                EvtKey evt( getIntf(), key, state, mod );
                win.processEvent( evt );
            }
            return 0;
        }
        case WM_WINDOWPOSCHANGING:
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
            // Snap, Win+arrows, system drag or maximize: keep the skin in sync.
            // Ignored while the plugin itself drives the geometry (self move),
            // and while the window is minimized.
            WINDOWPOS *pPos = (WINDOWPOS*)lParam;
            bool geomChanged = !(pPos->flags & SWP_NOMOVE) ||
                               !(pPos->flags & SWP_NOSIZE);
            if( win.isSnappable() && geomChanged && !win.isSelfMoving() &&
                !IsIconic( hwnd ) )
            {
                // The skin is the client area: the sizing borders of the
                // window lie around it
                RECT rc;
                POINT origin = { 0, 0 };
                if( GetClientRect( hwnd, &rc ) &&
                    ClientToScreen( hwnd, &origin ) )
                    win.onOSGeometryChange( origin.x, origin.y,
                                            rc.right, rc.bottom,
                                            IsZoomed( hwnd ) != 0 );
            }
            break;
        }
        case WM_NCCALCSIZE:
        {
            // No caption and no border at the top: the skin draws the whole
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
            // A window that draws its own frame has to give back the
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
                else if( win.isMaximizeButtonAt( pt.x, pt.y ) )
                {
                    // The maximize button of the skin: on Windows 11 the
                    // system shows the snap layouts menu over it
                    hit = HTMAXBUTTON;
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
            return hit;
        }
        case WM_NCMOUSEMOVE:
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
        {
            if( win.isSnappable() )
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
}


int Win32Loop::getMod( WPARAM wParam ) const
{
    int mod = EvtInput::kModNone;
    if( wParam & MK_CONTROL )
        mod |= EvtInput::kModCtrl;
    if( wParam & MK_SHIFT )
        mod |= EvtInput::kModShift;

    return mod;
}


void Win32Loop::exit()
{
    PostQuitMessage(0);
}

#endif
