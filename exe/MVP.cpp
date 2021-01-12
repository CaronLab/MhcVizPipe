// Simple C program to display "Hello World" 
  
// Header file for input output functions 
#include "exe_dir.h"
#include <sys/stat.h>
#include <boost/predef/os.h>

// test if a file exists
inline bool file_exists (const std::string& name) {
  struct stat buffer;   
  return (stat (name.c_str(), &buffer) == 0); 
}
  
// main function - 
// where the execution of program begins 
int main() 
{
    // get executable
    std::string exec = getExecutablePath();
    std::size_t botDirPos = exec.find_last_of("/");
    // get directory
    std::string dir = exec.substr(0, botDirPos);
    // make command
    std::string cmd;
    if (BOOST_OS_MACOS){
        cmd = dir + "/tools/MhcVizPipe --standalone";
    }
    else {
        if (BOOST_OS_LINUX){
            if (file_exists("/bin/gnome-terminal")){
                cmd = "gnome-terminal -- " + dir + "/tools/MhcVizPipe --standalone";
            }
            else if (file_exists("/bin/konsole/")){
                cmd = "konsole -e " + dir + "/tools/MhcVizPipe --standalone";
            }
            else if (file_exists("/bin/terminator/")){
                cmd = "terminator -e " + dir + "/tools/MhcVizPipe --standalone";
            }
            else if (file_exists("/bin/xterm/")){
                cmd = "xterm -e " + dir + "/tools/MhcVizPipe --standalone";
            }
            else if (file_exists("/bin/aterm/")){
                cmd = "aterm -e " + dir + "/tools/MhcVizPipe --standalone";
            }
            else{
                printf("%s\n", "Sorry, your terminal emulator was not automatically detected. Please start MhcVizPipe from the terminal manually.");
                return 1;
            }
        }
    }
    printf("%s", (cmd).c_str());
    system((cmd).c_str());
    return 0;
}
