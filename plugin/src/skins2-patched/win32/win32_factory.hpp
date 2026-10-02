/*****************************************************************************
 * win32_factory.hpp (modified in 2026 for the VLC Aurora kit: see plugin/LEGGIMI.txt)
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

#ifndef WIN32_FACTORY_HPP
#define WIN32_FACTORY_HPP

#ifdef HAVE_CONFIG_H
# include "config.h"
#endif

#include <windows.h>
#include <shellapi.h>
// #include <wingdi.h>
#include "../src/os_factory.hpp"
#include "../src/generic_window.hpp"

#include <map>
#include <set>
#include <vector>


/// Class used to instantiate Win32 specific objects
class Win32Factory: public OSFactory
{
public:
    Win32Factory( intf_thread_t *pIntf );
    virtual ~Win32Factory();

    /// Initialization method
    virtual bool init();

    /// Instantiate an object OSGraphics
    virtual OSGraphics *createOSGraphics( int width, int height );

    /// Get the instance of the singleton OSLoop
    virtual OSLoop *getOSLoop();

    /// Destroy the instance of OSLoop
    virtual void destroyOSLoop();

    /// Minimize all the windows
    virtual void minimize();

    /// Restore the minimized windows
    virtual void restore();

    /// Add an icon in the system tray
    virtual void addInTray();

    /// Remove the icon from the system tray
    virtual void removeFromTray();

    /// Show the task in the task bar
    virtual void addInTaskBar();

    /// Remove the task from the task bar
    virtual void removeFromTaskBar();

    /// Instantiate an OSTimer with the given command
    virtual OSTimer *createOSTimer( CmdGeneric &rCmd );

    /// Instantiate an OSWindow object
    virtual OSWindow *createOSWindow( GenericWindow &rWindow,
                                      bool dragDrop, bool playOnDrop,
                                      OSWindow *pParent,
                                      GenericWindow::WindowType_t type );

    /// Instantiate an object OSTooltip
    virtual OSTooltip *createOSTooltip();

    /// Instantiate an object OSPopup
    virtual OSPopup *createOSPopup();

    /// Get the directory separator
    virtual const std::string &getDirSeparator() const { return m_dirSep; }

    /// Get the resource path
    virtual const std::list<std::string> &getResourcePath() const
        { return m_resourcePath; }

    /// Get the screen size
    virtual int getScreenWidth() const;
    virtual int getScreenHeight() const;

    /// Get Monitor Information
    virtual void getMonitorInfo( const GenericWindow &rWindow,
                                 int* x, int* y,
                                 int* width, int* height ) const;
    virtual void getMonitorInfo( int numScreen,
                                 int* x, int* y,
                                 int* width, int* height ) const;

    /// Get the work area (screen area without taskbars)
    virtual SkinsRect getWorkArea() const;

    /// Get the position of the mouse
    virtual void getMousePos( int &rXPos, int &rYPos ) const;

    /// Change the cursor
    virtual void changeCursor( CursorType_t type ) const;

    /// Delete a directory recursively
    virtual void rmDir( const std::string &rPath );

    /// Map to find the GenericWindow associated with a Win32Window
    std::map<HWND, GenericWindow*> m_windowMap;

    HWND getParentWindow() { return m_hParentWindow; }

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

    /// Callback function (Windows Procedure)
    static LRESULT CALLBACK Win32Proc( HWND hwnd, UINT uMsg,
                                       WPARAM wParam, LPARAM lParam );

    /// Callback (enumerate multiple screens)
    static BOOL CALLBACK MonitorEnumProc( HMONITOR hMonitor, HDC hdcMonitor,
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
    std::set<HWND> m_madeTopmost;
    /// Handle of the instance
    HINSTANCE m_hInst;
    /// Handle of the parent window
    HWND m_hParentWindow;
    /// Structure for the system tray
    NOTIFYICONDATA m_trayIcon;
    /// Handle on msimg32.dll (for TransparentBlt)
    HINSTANCE m_hMsimg32;
    /// Handle on user32.dll (for SetLayeredWindowAttributes)
    HINSTANCE m_hUser32;
    /// Directory separator
    const std::string m_dirSep;
    /// Resource path
    std::list<std::string> m_resourcePath;
    /// Monitors detected
    std::list<HMONITOR> m_monitorList;
};


#endif
