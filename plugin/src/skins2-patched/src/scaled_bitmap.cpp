/*****************************************************************************
 * scaled_bitmap.cpp (modified in 2026 for the VLC Aurora kit: see plugin/LEGGIMI.txt)
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

#include "scaled_bitmap.hpp"
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


ScaledBitmap::~ScaledBitmap()
{
    delete[] m_pData;
}

