/*****************************************************************************
 * scaled_bitmap.hpp (modified in 2026 for the VLC Aurora kit: see plugin/LEGGIMI.txt)
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

#ifndef SCALED_BITMAP_HPP
#define SCALED_BITMAP_HPP

#include "generic_bitmap.hpp"


/// Class for scaling bitmaps
class ScaledBitmap: public GenericBitmap
{
public:
    /// Create a scaled bitmap from the given bitmap and size
    ScaledBitmap( intf_thread_t *pIntf, const GenericBitmap &rBitmap,
                  int width, int height );

    /// Create only a part of it: the rectangle (xPart, yPart, partWidth,
    /// partHeight) of the given bitmap scaled to width x height
    ScaledBitmap( intf_thread_t *pIntf, const GenericBitmap &rBitmap,
                  int width, int height,
                  int xPart, int yPart, int partWidth, int partHeight );

    virtual ~ScaledBitmap();

    /// Get the width of the bitmap
    virtual int getWidth() const { return m_width; }

    /// Get the heighth of the bitmap
    virtual int getHeight() const { return m_height; }

    /// Get a linear buffer containing the image data.
    /// Each pixel is stored in 4 bytes in the order B,G,R,A
    virtual uint8_t *getData() const { return m_pData; }

private:
    /// Bitmap size
    int m_width, m_height;
    /// Image data buffer
    uint8_t *m_pData;

    /// Fill the buffer with the part starting at (xPart, yPart) of the given
    /// bitmap scaled to width x height
    void scale( const GenericBitmap &rBitmap, int width, int height,
                int xPart, int yPart );
};


#endif
