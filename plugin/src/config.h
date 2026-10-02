/* config.h minimale per compilare il modulo skins2 di VLC 3.0.24 con mingw-w64 (MSYS2, msvcrt).
   Replica le definizioni HAVE_* rilevanti del build ufficiale per Windows; alla fine include
   vlc_fixups.h come fa il config.h generato da configure (AH_BOTTOM). */
#ifndef VLC_KIT_CONFIG_H
#define VLC_KIT_CONFIG_H
/* AC_USE_SYSTEM_EXTENSIONS */
#define _GNU_SOURCE 1
/* API Unicode di Windows, come il build ufficiale */
#define UNICODE 1
#define _UNICODE 1
#define HAVE_MAX_ALIGN_T 1
#define HAVE_STATIC_ASSERT 1
#define HAVE_LRINT 1
#define HAVE_LRINTF 1
#define PACKAGE "vlc"
#define PACKAGE_NAME "vlc"
#define PACKAGE_VERSION "3.0.24"
#define VERSION "3.0.24"
#define VERSION_MESSAGE "3.0.24 Vetinari"
#define COPYRIGHT_YEARS "1996-2025"
#define COPYRIGHT_MESSAGE "Copyright 1996-2025 the VideoLAN team"
#define HAVE_STRUCT_TIMESPEC 1
#define HAVE_STRUCT_POLLFD 1
#define HAVE_STRDUP 1
#define HAVE_STRNLEN 1
#define HAVE_STRNDUP 1
#define HAVE_STRCASECMP 1
#define HAVE_STRTOK_R 1
#define HAVE_STRTOF 1
#define HAVE_STRTOLL 1
#define HAVE_ATOF 1
#define HAVE_ATOLL 1
#define HAVE_LLDIV 1
#define HAVE_SWAB 1
#define HAVE_GETPID 1
#define HAVE_REWIND 1
#define HAVE_GETENV 1
#define HAVE_GETTIMEOFDAY 1
#define HAVE_SEARCH_H 1
#define HAVE_NANF 1
#define HAVE_TIMESPEC_GET 1
#define HAVE_INET_PTON 1
#define HAVE_IF_NAMETOINDEX 1
/* equivalente C99 di restrict per il C++ (AC_C_RESTRICT) */
#ifdef __cplusplus
# define restrict __restrict
#endif
#include <vlc_fixups.h>
#endif
