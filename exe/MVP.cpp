#include "exe_dir.h"
#include <sys/stat.h>
#include <boost/predef/os.h>
#include <boost/algorithm/string/predicate.hpp>

// test if a file exists
bool file_exists (const std::string& name) {
  struct stat buffer;
  return (stat (name.c_str(), &buffer) == 0);
}

std::string format_terminal_call(std::string term, std::string command){
    if (term == "mate-terminal -e " || term == "terminator - e " || term == "tilda -c " || term == "xfce4-terminal -e "){
        return term + "\"" + command + "\"";
    }
    else {
        return term + command;
    }
}

std::string format_terminal_bash_call(std::string term, std::string command){
    if (term == "mate-terminal -e " || term == "terminator - e " || term == "tilda -c " || term == "xfce4-terminal -e "){
        return term + "\"" + "/bin/bash -c \\\"" + command + "\\\"\"";
    }
    else {
        return term + "/bin/bash -c \"" + command + "\"";
    }
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
    // make command snf terminal strings
    std::string cmd = dir + "/MhcVizPipe.sh";
    std::string term;

    if (BOOST_OS_MACOS){
        // we don't need to specify Terminal, it will open automatically
        term = "";
    }
    else {
        if (BOOST_OS_LINUX){
            // its linux, try to find a terminal emulator to use
            if (file_exists("/bin/gnome-terminal") || file_exists("/usr/bin/gnome-terminal")){
                term = "gnome-terminal -- ";
            }
            else if (file_exists("/bin/konsole") || file_exists("/usr/bin/konsole")){
                term = "konsole -e ";
            }
            else if (file_exists("/bin/mate-terminal") || file_exists("/usr/bin/mate-terminal")){
                // mate-terminal requires us to enclose the command in quotes
                term = "mate-terminal -e ";
            }
            else if (file_exists("/bin/x-terminal-emulator") || file_exists("/usr/bin/x-terminal-emulator")){
                term = "x-terminal-emulator -e ";
            }
            else if (file_exists("/bin/terminator") || file_exists("/usr/bin/terminator")){
                // so does terminator
                term = "terminator - e ";
            }
            else if (file_exists("/bin/xterm") || file_exists("/usr/bin/xterm")){
                term = "xterm -e ";
            }
            else if (file_exists("/bin/aterm") || file_exists("/usr/bin/aterm")){
                term = "aterm -e ";
            }
            else if (file_exists("/bin/tilda") || file_exists("/usr/bin/tilda")){
                // tilda requires the quotes and uses -c instead of -e
                term = "tilda -c ";
            }
            else if (file_exists("/bin/xfce4-terminal") || file_exists("/usr/bin/xfce4-terminal")){
                // requires quotes
                term = "xfce4-terminal -e ";
            }
            else{
                return 1;
            }
        }
        else{
            // we are hopefully in Windows
            term = "start powershell -NoExit -Command "; // I think this will work, but we might need to explicitly invoke "wsl" as part of the command
        }
    }
    // check that the executable is probably in the correct directory
    if (! boost::algorithm::ends_with(dir, "MhcVizPipe")){
        std::string msg = std::string("") +
            "ERROR: It looks like the MhcVizPipe executable has been moved out of its installation directory or the "+
            "installation directory has been renamed. The executable needs to remain inside the installation directory and the "+
            "installation directory must not be renamed (i.e. it should still be called MhcVizPipe).\nPress any key to exit...\n";
        std::string call = "read -rsp $'" + msg + "' -n1 key";
        cmd = format_terminal_bash_call(term, call);
        system((cmd).c_str());
        return 1;
    }
    else if (! file_exists(dir + "/MhcVizPipe.sh")){
        std::string msg = std::string("") +
            "ERROR: The MhcVizPipe.sh file is missing from the MhcVizPipe folder. If you have moved it, please move it back to " +
            "its original location. If it has been deleted or is missing, you will need download it from " +
            "https://github.com/CaronLab/MhcVizPipe/tree/master/exe and place it in the MhcVizPipe directory.\nPress any key to exit...\n";
        std::string call = "read -rsp $'" + msg + "' -n1 key";
        cmd = format_terminal_bash_call(term, call);
        system((cmd).c_str());
        return 1;
    }

    // make sure that the MhcVizPipe script is executable
    if (BOOST_OS_MACOS){
        system(("xattr -r -s -d com.apple.quarantine " + dir + "/MhcVizPipe.sh; " + "chmod +x " + dir + "/MhcVizPipe.sh").c_str());
    }
    else{
        system(("chmod +x " + dir + "/MhcVizPipe.sh").c_str());
    }
    // and now execute it
    int return_code = system((format_terminal_call(term, cmd)).c_str());

    if (return_code != 0){
        std::string msg = std::string("")+"There was an unhandled error running MhcVizPipe. If you see an open terminal with an error message, take note of it. If not, "+
            "try running MhcVizPipe directly from the terminal using the following command:\n\n" +
            dir + "/MhcVizPipe.sh\n\n"+
            "If you do this but see a \"permission denied\" error when you run MhcVizPipe.sh try the following command to fix it before trying again:\n\n"+
            "chmod +x " + dir + "/MhcVizPipe.sh\n\n" +
            "If there is no obvious solution from the error message, please contact the developers by email or at:\n\n\thttps://github.com/CaronLab/MhcVizPipe/issues"+
            "\n\nPress any key to exit...\n";
        std::string call = "read -rsp $'" + msg + "' -n1 key";
        cmd = format_terminal_bash_call(term, call);
        system((cmd).c_str());
        return 1;
    }
    return 0;
}

