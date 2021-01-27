#if __has_include( <gtk/gtk.h> )
    #include <gtk/gtk.h>
#elif __has_include( <CoreFoundation/CoreFoundation.h> )
    #include <CoreFoundation/CoreFoundation.h>
#endif
#include "exe_dir.h"
#include <sys/stat.h>
#include <boost/predef/os.h>
#include <boost/algorithm/string/predicate.hpp>

// test if a file exists
inline bool file_exists (const std::string& name) {
  struct stat buffer;
  return (stat (name.c_str(), &buffer) == 0);
}

#if (BOOST_OS_MACOS)
    void show_error(const char *message, const char *title) {
        SInt32 nRes = 0;
        CFUserNotificationRef pDlg = NULL;
        const void* keys[] = { kCFUserNotificationAlertHeaderKey,
            kCFUserNotificationAlertMessageKey };
        const void* vals[] = {
            CFStringCreateWithCString(NULL, title, kCFStringEncodingUTF8),
            CFStringCreateWithCString(NULL, message, kCFStringEncodingUTF8)
        };

        CFDictionaryRef dict = CFDictionaryCreate(0, keys, vals,
                sizeof(keys)/sizeof(*keys),
                &kCFTypeDictionaryKeyCallBacks,
                &kCFTypeDictionaryValueCallBacks);

        pDlg = CFUserNotificationCreate(kCFAllocatorDefault, 0,
                     kCFUserNotificationPlainAlertLevel,
                     &nRes, dict);
    }
#else
    void show_error(const char *message, const char *title) {
        if (!gtk_init_check(0, nullptr)) {
          return;
       }

       // Create a parent window to stop gtk_dialog_run from complaining
       GtkWidget *parent = gtk_window_new(GTK_WINDOW_TOPLEVEL);

       GtkWidget *dialog = gtk_message_dialog_new(GTK_WINDOW(parent),
                                                  GTK_DIALOG_MODAL,
                                                  GTK_MESSAGE_ERROR,
                                                  GTK_BUTTONS_OK,
                                                  "%s",
                                                  message);
       gtk_window_set_title(GTK_WINDOW(dialog), title);
       gtk_dialog_run(GTK_DIALOG(dialog));
       gtk_widget_destroy(GTK_WIDGET(dialog));
       gtk_widget_destroy(GTK_WIDGET(parent));
       while (g_main_context_iteration(nullptr, false));
    }
#endif

// main function -
// where the execution of program begins
int main()
{
    // get executable
    std::string exec = getExecutablePath();
    std::size_t botDirPos = exec.find_last_of("/");
    // get directory
    std::string dir = exec.substr(0, botDirPos);
    // check that it looks like we are in the correct directory
    if (! boost::algorithm::ends_with(dir, "MhcVizPipe")){
        std::string msg = std::string("") +
            "It looks like the MhcVizPipe executable has been moved out of its installation directory or the "+
            "installation directory has been renamed. The executable needs to remain inside the installation directory and the "+
            "installation directory must not be renamed (i.e. it should still be called MhcVizPipe).";
        show_error((msg).c_str(), "Error");
        return 1;
    }
    // check that the tool directory is there
    if (! file_exists(dir + "/tools")){
        std::string msg = std::string("") +
            "The \"tools\" folder is missing from the MhcVizPipe folder. If you have moved it, please move it back to "+
            "its original location. If it has been deleted or is missing, you will need to reinstall MhcVizPipe (or replace the tool " +
            "folder by extracting it from the MhcVizPipe download).";
        show_error((msg).c_str(), "Error");
        return 1;
    }
    // check that the python directory is there
    if (! file_exists(dir + "/python")){
        std::string msg = std::string("") +
            "The \"python\" folder is missing from the MhcVizPipe folder. If you have moved it, please move it back to "+
            "its original location. If it has been deleted or is missing, you will need to reinstall MhcVizPipe (or replace the python "+
            "folder by extracting it from the MhcVizPipe download).";
        show_error((msg).c_str(), "Error");
        return 1;
    }
    // check that all the scripts are there
    if (!file_exists(dir + "/tools/gibbscluster") |
        !file_exists(dir + "/tools/netMHCIIpan") |
        !file_exists(dir + "/tools/netMHCpan4.0") |
        !file_exists(dir + "/tools/netMHCpan4.1") ){
        std::string msg = std::string("") +
            "One or more of the tool scripts are missing from the \"tools\" folder. It should have the following contents: "+
            "netMHCpan4.0, netMHCpan4.1, netMHCIIpan, and gibbscluster. Please replace these files either by downloading them from "+
            "https://github.com/CaronLab/MhcVizPipe/tree/master/tool_scripts or extracting them from your original MhcVizPipe download "+
            "(if you still have it).";
        show_error((msg).c_str(), "Error");
        return 1;
    }

    // make command string
    std::string cmd;
    // make sure MVP can execute the tool scripts and that the MhcVizPipe script is also executable
    system(("chmod +x " + dir + "/tools/gibbscluster; " +
            "chmod +x " + dir + "/tools/netMHCIIpan; " +
            "chmod +x " + dir + "/tools/netMHCpan4.0; " +
            "chmod +x " + dir + "/tools/netMHCpan4.1; " +
            "chmod +x " + dir + "/MhcVizPipe.sh").c_str());

    if (BOOST_OS_MACOS){
        printf("%s\n", "\nPreparing directory contents");
        // remove the quarantine attribute from needed things if it is there
        std::string unquarantine = "xattr -r -s -d com.apple.quarantine " + dir + "/tools/ " + dir + "/python " + dir + "/MhcVizPipe.sh";
        system((unquarantine).c_str());
        // we don't need to specify Terminal, it will open automatically
        cmd = dir + "/python/bin/python3 -m MhcVizPipe.gui --standalone";
    }
    else {
        if (BOOST_OS_LINUX){
            // its linux, try to find a terminal emulator to use
            if (file_exists("/bin/gnome-terminal") | file_exists("/usr/bin/gnome-terminal")){
                cmd = "gnome-terminal -- " + dir + "/python/bin/python3 -m MhcVizPipe.gui --standalone";
            }
            else if (file_exists("/bin/konsole/") | file_exists("/usr/bin/konsole/")){
                cmd = "konsole -e " + dir + "/python/bin/python3 -m MhcVizPipe.gui --standalone";
            }
            else if (file_exists("/bin/terminator/") | file_exists("/usr/bin/terminator/")){
                cmd = "terminator -e " + dir + "/python/bin/python3 -m MhcVizPipe.gui --standalone";
            }
            else if (file_exists("/bin/xterm/") | file_exists("/usr/bin/xterm/")){
                cmd = "xterm -e " + dir + "/python/bin/python3 -m MhcVizPipe.gui --standalone";
            }
            else if (file_exists("/bin/aterm/") | file_exists("/usr/bin/aterm/")){
                cmd = "aterm -e " + dir + "/python/bin/python3 -m MhcVizPipe.gui --standalone";
            }
            else if (file_exists("/bin/tilda/") | file_exists("/usr/bin/tilda/")){
                cmd = "tilda -e " + dir + "/python/bin/python3 -m MhcVizPipe.gui --standalone";
            }
            else if (file_exists("/bin/xfce4-terminal/") | file_exists("/usr/bin/xfce4-terminal/")){
                cmd = "xfce4-terminal -e " + dir + "/python/bin/python3 -m MhcVizPipe.gui --standalone";
            }
            else{
                std::string message = std::string("") +
                    "Sorry, your terminal emulator was not automatically detected. Please start MhcVizPipe from the terminal manually using the provided " +
                    "shell script (MhcVizPipe.sh). If you need the full path to the script, here it is:\n\n" +
                    dir + "/MhcVizPipe.shn\n\n" +
                    "If you type that into you terminal and hit enter, MhcVizPipe should hopefully start up. If you see a \"permission denied\" error try " +
                    "the following command to fix it before trying again:\n\n" +
                    "chmod +x " + dir + "/MhcVizPipe.sh";
                show_error((message).c_str(), "Error");
                return 1;
            }
        }
    }
    int return_code = system((cmd).c_str());
    if (return_code != 0){
        std::string message = std::string("")+"There was an unhandled error starting MhcVizPipe. If you see an open terminal with an error message, take note of it. If not, "+
        "try running MhcVizPipe directly from the terminal using the following command:\n\n" +
        dir + "/MhcVizPipe.sh\n\n"+
        "If you do this but see a \"permission denied\" error when you run MhcVizPipe.sh try the following command to fix it before trying again:\n\n"+
        "chmod +x " + dir + "/MhcVizPipe.sh\n\n";
        "If there is no obvious solution from the error message, please contact the developers by email or at:\n\n\thttps://github.com/CaronLab/MhcVizPipe/issues";
        show_error((message).c_str(), "Error");
    }
    return 0;
}

