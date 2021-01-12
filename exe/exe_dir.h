#ifndef __EXE_DIR_H__
#define __EXE_DIR_H__

#include <string>
#include <boost/predef/os.h>
#include <boost/filesystem.hpp>

#if (BOOST_OS_WINDOWS)
#  include <stdlib.h>
#elif (BOOST_OS_SOLARIS)
#  include <stdlib.h>
#  include <limits.h>
#elif (BOOST_OS_LINUX)
#  include <unistd.h>
#  include <limits.h>
#elif (BOOST_OS_MACOS)
#  include <mach-o/dyld.h>
#elif (BOOST_OS_BSD_FREE)
#  include <sys/types.h>
#  include <sys/sysctl.h>
#endif

/*
 * @Return the full path to the currently running executable,
 * or an empty string in case of failure.
 */
std::string getExecutablePath() {
#if (BOOST_OS_WINDOWS)
    char *exePath;
    if (_get_pgmptr(&exePath) != 0)
        exePath = "";
#elif (BOOST_OS_SOLARIS)
    char exePath[PATH_MAX];
    if (realpath(getexecname(), exePath) == NULL)
        exePath[0] = '\0';
#elif (BOOST_OS_LINUX)
    char exePath[PATH_MAX];
    ssize_t len = ::readlink("/proc/self/exe", exePath, sizeof(exePath));
    if (len == -1 || len == sizeof(exePath))
        len = 0;
    exePath[len] = '\0';
#elif (BOOST_OS_MACOS)
    char exePath[PATH_MAX];
    uint32_t len = sizeof(exePath);
    if (_NSGetExecutablePath(exePath, &len) != 0) {
        exePath[0] = '\0'; // buffer too small (!)
    } else {
        // resolve symlinks, ., .. if possible
        char *canonicalPath = realpath(exePath, NULL);
        if (canonicalPath != NULL) {
            strncpy(exePath,canonicalPath,len);
            free(canonicalPath);
        }
    }
#elif (BOOST_OS_BSD_FREE)
    char exePath[2048];
    int mib[4];  mib[0] = CTL_KERN;  mib[1] = KERN_PROC;  mib[2] = KERN_PROC_PATHNAME;  mib[3] = -1;
    size_t len = sizeof(exePath);
    if (sysctl(mib, 4, exePath, &len, NULL, 0) != 0)
        exePath[0] = '\0';
#endif
    return std::string(exePath);
}

// NOTE: to return the path without the executable name:
//#include boost/filesystem.hpp>
// and change the last line to:
//return strlen(exePath)>0 ? boost::filesystem::path(exePath).remove_filename().make_preferred().string() : std::string();

#endif // __EXE_DIR_H__
