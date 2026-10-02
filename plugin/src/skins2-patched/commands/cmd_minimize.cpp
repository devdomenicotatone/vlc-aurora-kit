/*****************************************************************************
 * cmd_minimize.cpp (modified in 2026 for the VLC Aurora kit: see plugin/LEGGIMI.txt)
 *****************************************************************************
 * Copyright (C) 2003 the VideoLAN team
 * $Id$
 *
 * Authors: Mohammed Adnène Trojette     <adn@via.ecp.fr>
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

#include "cmd_minimize.hpp"
#include "../src/window_manager.hpp"
#include "../src/os_factory.hpp"

#ifdef _WIN32
# include <shellapi.h>
#endif


void CmdOpenLink::execute()
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
{
#ifdef _WIN32
    // The HTTP interface listens on http-port (8080 unless changed)
    int port = (int)var_InheritInteger( getIntf(), "http-port" );
    wchar_t url[64];
    _snwprintf( url, 64, L"http://localhost:%d/", port );
    url[63] = L'\0';
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
{
    OSFactory::instance( getIntf() )->minimize();
}


void CmdRestore::execute()
{
    OSFactory::instance( getIntf() )->restore();
}


CmdMaximize::CmdMaximize( intf_thread_t *pIntf, WindowManager &rWindowManager,
                          TopWindow &rWindow )
    : CmdGeneric( pIntf ), m_rWindowManager( rWindowManager ),
      m_rWindow( rWindow ) { }


void CmdMaximize::execute()
{
    // Simply delegate the job to the WindowManager
    m_rWindowManager.maximize( m_rWindow );
}


CmdUnmaximize::CmdUnmaximize( intf_thread_t *pIntf,
                              WindowManager &rWindowManager,
                              TopWindow &rWindow )
    : CmdGeneric( pIntf ), m_rWindowManager( rWindowManager ),
      m_rWindow( rWindow ) { }


void CmdUnmaximize::execute()
{
    // Simply delegate the job to the WindowManager
    m_rWindowManager.unmaximize( m_rWindow );
}


void CmdAddInTray::execute()
{
    OSFactory::instance( getIntf() )->addInTray();
}


void CmdRemoveFromTray::execute()
{
    OSFactory::instance( getIntf() )->removeFromTray();
}


void CmdAddInTaskBar::execute()
{
    OSFactory::instance( getIntf() )->addInTaskBar();
}


void CmdRemoveFromTaskBar::execute()
{
    OSFactory::instance( getIntf() )->removeFromTaskBar();
}

