/*****************************************************************************
 * win32_window.hpp (modified in 2026 for the VLC Aurora kit: see plugin/LEGGIMI.txt)
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
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston MA 02110-1301, USA.
 *****************************************************************************/

#ifndef WIN32_WINDOW_HPP
#define WIN32_WINDOW_HPP

#include "../src/generic_window.hpp"
#include "../src/os_window.hpp"
#include <windows.h>
#include <ole2.h>   // LPDROPTARGET


/// Win32 implementation of OSWindow
class Win32Window: public OSWindow
{
public:
    Win32Window( intf_thread_t *pIntf, GenericWindow &rWindow,
                 HINSTANCE hInst, HWND hParentWindow,
                 bool dragDrop, bool playOnDrop,
                 Win32Window *pParentWindow, GenericWindow::WindowType_t );
    virtual ~Win32Window();

    // Show the window
    virtual void show() const;

    // Hide the window
    virtual void hide() const;

    /// Move and resize the window
    virtual void moveResize( int left, int top, int width, int height ) const;

    /// Bring the window on top
    virtual void raise() const;

    /// Set the opacity of the window (0 = transparent, 255 = opaque)
    virtual void setOpacity( uint8_t value ) const;

    /// Toggle the window on top
    virtual void toggleOnTop( bool onTop ) const;

    /// Getter for the window handle
    HWND getHandle() const { return m_hWnd; }

    /// Getter for the window handle
    void* getOSHandle() const { return (void*) m_hWnd; }

    /// reparent the window
    void reparent( void* OSHandle, int x, int y, int w, int h );

    /// invalidate a window surface
    bool invalidateRect( int x, int y, int w, int h ) const;

    /// Snap support (top-level skin windows only)
    virtual bool isSnappable() const { return m_snappable; }

    /// System driven drag (SC_MOVE loop): Windows Snap, snap layouts, shake...
    virtual bool startNativeMove() const;

    /// System maximize / restore
    virtual bool setMaximized( bool maximized ) const;

    /// See OSWindow::isSelfMoving
    virtual bool isSelfMoving() const { return m_selfMove > 0; }

    /// Thickness of the sizing borders that a snappable window keeps on its
    /// left, right and bottom sides (none at the top). The system leaves
    /// them invisible; they lie around the area that the skin draws and
    /// are where the window is resized from.
    static void getSizingBorders( HWND hWnd, RECT *pBorders );

    /// Shape of a snappable window. A rectangular one (systemFrame) is left
    /// without region, so that the DWM renders its frame: shadow and, on
    /// Windows 11, rounded corners and a border in the given colour. A
    /// shaped one keeps the region that the caller applies.
    void setSystemFrame( bool systemFrame, COLORREF border ) const;

private:
    /// Window handle
    HWND m_hWnd;
    /// Window parent's handle
    HWND m_hWnd_parent;
    /// Indicates whether the window handles drag&drop events
    bool m_dragDrop;
    /// Drop target
    LPDROPTARGET m_pDropTarget;
    /// Indicates whether the window is layered
    mutable bool m_isLayered;
    /// Parent window
    Win32Window *m_pParent;
    /// window type
    GenericWindow::WindowType_t m_type;
    /// true for top-level skin windows (system sizing frame, snappable)
    bool m_snappable;
    /// >0 while moveResize() drives the window (guards the OS-geometry sync)
    mutable int m_selfMove;
    /// true while a region is applied to the window (shaped skin)
    mutable bool m_hasRegion;
    /// border colour last given to the DWM (CLR_INVALID: none yet)
    mutable COLORREF m_borderColor;

};


#endif
