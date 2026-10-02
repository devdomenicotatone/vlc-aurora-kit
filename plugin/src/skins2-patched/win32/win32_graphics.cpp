/*****************************************************************************
 * win32_graphics.cpp (modified in 2026 for the VLC Aurora kit: see plugin/LEGGIMI.txt)
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
#include "win32_graphics.hpp"
#include "win32_window.hpp"
#include "../src/generic_bitmap.hpp"
#include <cstring>
#include <vector>

#ifndef AC_SRC_ALPHA
#define AC_SRC_ALPHA 1
#endif

Win32Graphics::Win32Graphics( intf_thread_t *pIntf, int width, int height ):
    OSGraphics( pIntf ), m_width( width ), m_height( height ), m_hDC( NULL )
{
    HBITMAP hBmp;
    HDC hDC = GetDC( NULL );
    hBmp = CreateCompatibleBitmap( hDC, m_width, m_height );
    ReleaseDC( NULL, hDC );

    m_hDC = CreateCompatibleDC( NULL );
    SelectObject( m_hDC, hBmp );
    DeleteObject( hBmp );

    // Create the mask
    m_mask = CreateRectRgn( 0, 0, 0, 0 );
}


Win32Graphics::~Win32Graphics()
{
    DeleteDC( m_hDC );
    DeleteObject( m_mask );
}


void Win32Graphics::clear( int xDest, int yDest, int width, int height )
{
    if( width <= 0 || height <= 0 )
    {
        // Clear the transparency mask
        DeleteObject( m_mask );
        m_mask = CreateRectRgn( 0, 0, 0, 0 );
    }
    else
    {
        HRGN mask = CreateRectRgn( xDest, yDest,
                                   xDest + width, yDest + height );
        CombineRgn( m_mask, m_mask, mask, RGN_DIFF );
        DeleteObject( mask );
    }
}


void Win32Graphics::drawBitmap( const GenericBitmap &rBitmap,
                                int xSrc, int ySrc, int xDest, int yDest,
                                int width, int height, bool blend )
{
    (void)blend;

    // check and adapt to source if needed
    if( !checkBoundaries( 0, 0, rBitmap.getWidth(), rBitmap.getHeight(),
                          xSrc, ySrc, width, height ) )
    {
        msg_Err( getIntf(), "empty source! pls, debug your skin" );
        return;
    }

    // check destination
    if( !checkBoundaries( 0, 0, m_width, m_height,
                          xDest, yDest, width, height ) )
    {
        msg_Err( getIntf(), "out of reach destination! pls, debug your skin" );
        return;
    }

    // Get a buffer on the image data
    uint8_t *pBmpData = rBitmap.getData();
    if( pBmpData == NULL )
    {
        // Nothing to draw
        return;
    }

    // Visible segments of each line, for the transparency mask. They are
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


void Win32Graphics::drawGraphics( const OSGraphics &rGraphics, int xSrc,
                                  int ySrc, int xDest, int yDest, int width,
                                  int height )
{
    // check and adapt to source if needed
    if( !checkBoundaries( 0, 0, rGraphics.getWidth(), rGraphics.getHeight(),
                          xSrc, ySrc, width, height ) )
    {
        msg_Err( getIntf(), "nothing to draw from graphics source" );
        return;
    }

    // check destination
    if( !checkBoundaries( 0, 0, m_width, m_height,
                          xDest, yDest, width, height ) )
    {
        msg_Err( getIntf(), "out of reach destination! pls, debug your skin" );
        return;
    }

    // Create the mask for transparency
    HRGN mask = CreateRectRgn( xSrc, ySrc, xSrc + width, ySrc + height );
    CombineRgn( mask, ((Win32Graphics&)rGraphics).getMask(), mask, RGN_AND );
    OffsetRgn( mask, xDest - xSrc, yDest - ySrc );

    // Copy the image
    HDC srcDC = ((Win32Graphics&)rGraphics).getDC();
    SelectClipRgn( m_hDC, mask );
    BitBlt( m_hDC, xDest, yDest, width, height, srcDC, xSrc, ySrc, SRCCOPY );

    // Add the source mask to the mask of the graphics
    CombineRgn( m_mask, mask, m_mask, RGN_OR );
    DeleteObject( mask );
}


void Win32Graphics::fillRect( int left, int top, int width, int height,
                              uint32_t color )
{
    // Update the mask with the rectangle area
    HRGN newMask = CreateRectRgn( left, top, left + width, top + height );
    CombineRgn( m_mask, m_mask, newMask, RGN_OR );
    SelectClipRgn( m_hDC, m_mask );
    DeleteObject( newMask );

    // Create a brush with the color
    int red = (color & 0xff0000) >> 16;
    int green = (color & 0xff00) >> 8;
    int blue = color & 0xff;
    HBRUSH hBrush = CreateSolidBrush( RGB( red, green, blue ) );

    // Draw the rectangle
    RECT r;
    r.left = left;
    r.top = top;
    r.right = left + width;
    r.bottom = top + height;
    FillRect( m_hDC, &r, hBrush );
    DeleteObject( hBrush );
}


void Win32Graphics::drawRect( int left, int top, int width, int height,
                              uint32_t color )
{
    // Update the mask with the rectangle
    HRGN l1 = CreateRectRgn( left, top, left + width, top + 1 );
    HRGN l2 = CreateRectRgn( left + width - 1, top,
                             left + width, top + height );
    HRGN l3 = CreateRectRgn( left, top + height - 1,
                             left + width, top + height );
    HRGN l4 = CreateRectRgn( left, top, left + 1, top + height );
    CombineRgn( m_mask, m_mask, l1, RGN_OR );
    CombineRgn( m_mask, m_mask, l2, RGN_OR );
    CombineRgn( m_mask, m_mask, l3, RGN_OR );
    CombineRgn( m_mask, m_mask, l4, RGN_OR );
    DeleteObject( l1 );
    DeleteObject( l2 );
    DeleteObject( l3 );
    DeleteObject( l4 );

    SelectClipRgn( m_hDC, m_mask );

    // Create a pen with the color
    int red = (color & 0xff0000) >> 16;
    int green = (color & 0xff00) >> 8;
    int blue = color & 0xff;
    HPEN hPen = CreatePen( PS_SOLID, 0, RGB( red, green, blue ) );
    SelectObject( m_hDC, hPen );

    // Draw the rectangle
    MoveToEx( m_hDC, left, top, NULL );
    LineTo( m_hDC, left + width - 1, top );
    LineTo( m_hDC, left + width - 1, top + height - 1 );
    LineTo( m_hDC, left, top + height - 1 );
    LineTo( m_hDC, left, top );

    // Delete the pen
    DeleteObject( hPen );
}


void Win32Graphics::applyMaskToWindow( OSWindow &rWindow )
{
    // Get window handle
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

    // Apply the mask
    // We need to copy the mask, because SetWindowRgn modifies it in our back
    HRGN mask = CreateRectRgn( 0, 0, 0, 0 );
    CombineRgn( mask, m_mask, NULL, RGN_COPY );
    if( rWin.isSnappable() )
    {
        // The region is relative to the window, the mask to the area drawn
        // by the skin, which begins after the left sizing border
        RECT borders;
        Win32Window::getSizingBorders( hWnd, &borders );
        OffsetRgn( mask, borders.left, borders.top );
    }
    SetWindowRgn( hWnd, mask, TRUE );
}


void Win32Graphics::copyToWindow( OSWindow &rWindow, int xSrc, int ySrc,
                                  int width, int height, int xDest, int yDest )
{
    // Initialize painting
    HWND hWnd = ((Win32Window&)rWindow).getHandle();
    HDC wndDC = GetDC( hWnd );
    HDC srcDC = m_hDC;

    // Draw image on window
    BitBlt( wndDC, xDest, yDest, width, height, srcDC, xSrc, ySrc, SRCCOPY );

    // Release window device context
    ReleaseDC( hWnd, wndDC );
}


bool Win32Graphics::hit( int x, int y ) const
{
    return PtInRegion( m_mask, x, y ) != 0;
}


void Win32Graphics::addSegmentInRegion( HRGN &rMask, int start,
                                        int end, int line )
{
    HRGN buffer = CreateRectRgn( start, line, end, line + 1 );
    CombineRgn( rMask, buffer, rMask, RGN_OR );
    DeleteObject( buffer );
}


bool Win32Graphics::checkBoundaries( int x_src, int y_src,
                                     int w_src, int h_src,
                                     int& x_target, int& y_target,
                                     int& w_target, int& h_target )
{
    // set valid width and height
    w_target = (w_target > 0) ? w_target : w_src;
    h_target = (h_target > 0) ? h_target : h_src;

    // clip source if needed
    rect srcRegion( x_src, y_src, w_src, h_src );
    rect targetRegion( x_target, y_target, w_target, h_target );
    rect inter;
    if( rect::intersect( srcRegion, targetRegion, &inter ) )
    {
        x_target = inter.x;
        y_target = inter.y;
        w_target = inter.width;
        h_target = inter.height;
        return true;
    }
    return false;
}

#endif
