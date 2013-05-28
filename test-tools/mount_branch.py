import logging
import os
import pickle
import shutil
import socket
import sys
import subprocess
import urllib
from zipfile import ZipFile

def lexec(cmd, input=None, silent=False):
    """Launch a command"""

    if not silent:
        logging.info("\t%s" % cmd)
    
    cmd = cmd.split(" ") #TODO(bcipolli): do this properly lol

    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (cmd_stdout,cmd_stderr) = p.communicate(input=input)
    if p.returncode:
        if not silent:
            logging.warning("\t\tERROR: %s" % cmd_stderr)
    elif not silent:
        logging.debug("\t\tOutput: %s" % cmd_stdout)
        
    return (p.returncode, cmd_stdout, cmd_stderr)



def get_open_ports(port_range=(50000, 65000), num_ports=1):
    try:
        (_,stdout,_) = lexec("nmap 127.0.0.1 -p%d-%d" % port_range, silent=True)
    except:
        # If nmap doesn't exist, this will fail
        stdout = ""
        
    #Nmap scan report for localhost.localdomain (127.0.0.1)
    #Host is up (0.00056s latency).
    #Not shown: 999 closed ports
    #PORT     STATE SERVICE
    #9001/tcp open  tor-orport

    #Nmap done: 1 IP address (1 host up) scanned in 0.15 seconds
    import random;
    for i in range(100):
        port = port_range[0] + int(round(random.random()*(port_range[1]-port_range[0]+1)))
        
        # If any port in the sequence is taken, try again... (continue)
        for j in range(num_ports):
            if str(port+j) in stdout:
                continue
                
        # All ports were OK; get out!
        break
    
    return range(port, port+num_ports)
    
    
class KaLiteServer(object):
    admin_user = { 
        "username": "admin", 
        "email": "admin@example.com", 
        "password": "pass",
    }
    _pyexec = None
    
    def __init__(self, repo_dir, server_type, port, central_server_port=None):
        self.repo_dir = repo_dir
        self.server_type = server_type
        self.port = port
        self.central_server_port = port if (central_server_port is None and server_type=="central") else central_server_port
        
        self.admin_user = self.__class__.admin_user
        
    def start_server(self):
        """ """        
        cwd = os.getcwd()
        os.chdir(self.repo_dir)
    
        lexec(self.pyexec() + " kalite/manage.py runcherrypyserver host=0.0.0.0 port=%d threads=50 daemonize=true pidfile=kalite/runcherrypyserver.pid" % self.port)
    
        os.chdir(cwd)


    def pyexec(self):
        # Grab python, for all!
        if not self.__class__._pyexec:   
            (_,pyexec,_) = lexec("bash " + self.repo_dir+"/python.sh", silent=True)
            self.__class__._pyexec = pyexec[:-1]
        return self.__class__._pyexec
        
        
    def create_local_settings_file(self):
    
        # First, set up localsettings
        logging.info("Creating local_settings.py")
        local_settings = open(self.repo_dir+"/kalite/local_settings.py","w")

        local_settings.write("DEBUG = True\n")
        local_settings.write("TEMPLATE_DEBUG = True\n")

        hostname = socket.getfqdn()
    
        if self.server_type=="central":
            local_settings.write("CENTRAL_SERVER = True\n")
            local_settings.write("EMAIL_BACKEND = 'postmark.backends.PostmarkBackend'\n")
            local_settings.write("POSTMARK_API_KEY = 'f0b8e26a-6065-4611-a97d-6af27d89b3a6'\n")
            local_settings.write("CENTRAL_FROM_EMAIL    = 'ben@learningequality.org'\n")
            local_settings.write("CENTRAL_ADMIN_EMAIL   = 'ben@learningequality.org'\n")
            local_settings.write("CENTRAL_CONTACT_EMAIL = 'ben@learningequality.org'\n")

            local_settings.write("CENTRAL_DEPLOYMENT_EMAIL = 'ben@learningequality.org'\n")
            local_settings.write("CENTRAL_SUPPORT_EMAIL    = 'ben@learningequality.org'\n")
            local_settings.write("CENTRAL_DEV_EMAIL        = 'ben@learningequality.org'\n")
            local_settings.write("CENTRAL_INFO_EMAIL       = 'ben@learningequality.org'\n")

            # These should disappear
            local_settings.write("CENTRAL_SERVER_DOMAIN = '%s:%d'\n" % (hostname,self.central_server_port))
            local_settings.write("CENTRAL_SERVER_HOST = '%s:%d'\n" % (hostname,self.central_server_port))
        else:
            local_settings.write("CENTRAL_SERVER_DOMAIN = '%s:%d'\n" % (hostname,self.central_server_port))
            local_settings.write("CENTRAL_SERVER_HOST = '%s:%d'\n" % (hostname,self.central_server_port))
            local_settings.write("SECURESYNC_PROTOCOL = 'http'\n")
    
        local_settings.close()


    def install_server(self):
        # Then, make sure to run the installation
        logging.info("Creating the database and admin user")
        cwd = os.getcwd()
        os.chdir(self.repo_dir)
        if os.path.exists('kalite/database/data.sqlite'):
            os.remove('kalite/database/data.sqlite')

        lexec(self.pyexec() + " kalite/manage.py syncdb --migrate", input="no\n")
        lexec(self.pyexec() + " kalite/manage.py shell", input="from django.contrib.auth.models import User; User.objects.create_superuser('%s', '%s', '%s')" % (self.admin_user["username"], self.admin_user["email"], self.admin_user["password"]))
        lexec(self.pyexec() + " kalite/manage.py initdevice '%s' 'central_server_port=%d'" % (self.server_type, self.central_server_port))
    
        os.chdir(cwd)
    
    
    def setup_server(self):
        # Always destroy/rewrite the local settings
        self.create_local_settings_file()
        self.install_server()

    

class KaLiteProject(object):

    def __init__(self, git_user, repo_branch, git_repo="ka-lite", base_dir=os.path.dirname(os.path.realpath(__file__))):
        self.git_user = git_user
        self.repo_branch = repo_branch
        self.git_repo = git_repo
        self.base_dir = base_dir

        self.user_dir   = self.base_dir + "/" + self.git_user
        self.branch_dir = self.user_dir + "/" + self.repo_branch



    def get_repo_dir(self, server_type):
        return self.branch_dir+"/"+server_type
                                                             
    def setup_project(self, server_types, port_range=(50000, 65000), open_ports=None, port_map=None):
        """Sets up the branch directories, points to a directory for local and central"""
    
        assert port_range or open_ports or port_map, "Must pass either port_range or ports"
        assert not open_ports or len(open_ports)>=1, "Must pass in at least 1 port"
        assert not port_map or (hasattr(port_map,"keys") and len(port_map.keys())>=1), "Must pass in at least 1 port, as a dictionary on port_map"
        
        # Create the branch directory
        if os.path.exists(self.branch_dir):
            logging.debug("Using branch directory: %s" % self.branch_dir)
        else:
            logging.debug("Creating branch directory: %s" % self.branch_dir)
            os.makedirs(self.branch_dir)

        # get ports as a numeric list
        port_keys = set(server_types).union({"central"}) # must have a central server port
        if not port_map:
            if not open_ports:
                open_ports = get_open_ports(port_range=port_range, num_ports=2) # system call
            port_map = dict()
            for st in port_keys:
                p = self.__class__.get_ports_from_map([self.port_map_key(st),])
                port_map[st] = p[0] if p[0] else open_ports.pop()
        self.__class__.set_ports_to_map(dict(zip([self.port_map_key(st) for st in port_map.keys()], port_map.values())))
        self.__class__.save_port_map()
        
        # Setting up these servers, but they don't actually exist!
        # ... until we create them, that is! :D 
        self.servers = {}
        for server_type in server_types:
            self.servers[server_type] = KaLiteServer(repo_dir=self.get_repo_dir(server_type), 
                                                     server_type=server_type, 
                                                     port=port_map[server_type], 
                                                     central_server_port=port_map["central"])
    
    def mount_project(self, server_types, port_range=(50000, 65000), open_ports=None, port_map=None):
        """Convenience function to set up the project, then to mount it."""
        self.setup_project(server_types, port_range, open_ports, port_map)
        self.emit_header()
        self.mount()
        
                
    def port_map_key(self, server_type):
        return "%s/%s.git:%s %s" % (self.git_user, self.git_repo, self.repo_branch, server_type)

    def emit_header(self):
        # Emit an informative header
        logging.info("*"*50)
        logging.info("*")
        logging.info("* Setting up %s/%s.git:%s" % (self.git_user, self.git_repo, self.repo_branch))
        for key in self.servers.keys():
            logging.info("* \t%s server path: %s" % (key, self.servers[key].repo_dir))
        logging.info("*")
        for key in self.servers.keys():
            logging.info("* \t%s server URL: http://%s:%d/" % (key, socket.getfqdn(), self.servers[key].port))
        logging.info("*")
        logging.info("* Admin info (both servers):")
        logging.info("* \tusername: %s" % self.servers[self.servers.keys()[0]].admin_user["username"])
        logging.info("* \tpassword: %s" % self.servers[self.servers.keys()[0]].admin_user["password"])
        logging.info("* \temail: %s"    % self.servers[self.servers.keys()[0]].admin_user["email"])
        logging.info("*")
        logging.info("*"*50)
        logging.info("")





    port_map_file = os.path.dirname(os.path.realpath(__file__)) + "/port_map.pkl"
    port_map = None
    
    @classmethod
    def load_port_map(cls, port_map_file=None):
        if not port_map_file:
            port_map_file = cls.port_map_file
        try:
            fp = open(port_map_file, 'r')
            cls.port_map = pickle.load(fp)
            fp.close()
        except Exception as e:
            raise e
        return cls.port_map
    
    @classmethod
    def save_port_map(cls, port_map_file=None):
        if not port_map_file:
            port_map_file = cls.port_map_file 
        try:
            fp = open(port_map_file, 'w')
            pickle.dump(cls.port_map, fp)
            fp.close()
        except Exception as e:
            logging.warn("Failed to save port map: %s" % e.message)

    @classmethod
    def get_ports_from_map(cls, port_keys):
        if not cls.port_map:
            if os.path.exists(cls.port_map_file):
                cls.port_map = cls.load_port_map(cls.port_map_file)
            else:
                cls.port_map = dict()
        return [cls.port_map[pk] if pk in cls.port_map.keys() else None for pk in port_keys]
        
    @classmethod
    def set_ports_to_map(cls, port_map):
        if not cls.port_map:
            if os.path.exists(cls.port_map_file):
                cls.port_map = cls.load_port_map(cls.port_map_file)
            else:
                cls.port_map = dict()
        cls.port_map = dict(cls.port_map.items() + port_map.items())
    

class KaLiteRepoProject(KaLiteProject):
    def __init__(self, *args, **kwargs):
        super(KaLiteRepoProject, self).__init__(*args, **kwargs)


    def setup_repo(self, server):
        """Set up the specified user's repo as a remote; return the directory it's set up in!"""
    
        if self.git_repo != "ka-lite":
            raise NotImplementedError("Only ka-lite repo has been implemented!")
        
        logging.debug("Setting up %s %s %s" % (self.git_user, self.repo_branch, self.git_repo))
    
        # Create the branch directory
        self.branch_dir = os.path.realpath(server.repo_dir + "/..")
        if os.path.exists(self.branch_dir):
            logging.info("Mounting git to existing branch dir: %s" % self.branch_dir)
        else:
            logging.info("Creating branch dir")
            os.makedirs(self.branch_dir)


        # clone the git repository
        os.chdir(self.branch_dir)
        # Directory exists, maybe it's already set up? 
        if os.path.exists(server.repo_dir):
            os.chdir(server.repo_dir)
            (_,stdout,stderr) = lexec("git remote -v")
            # It contains the desired repo; good enough. 
            # TODO(bcipolli): really should check if the repo is ORIGIN
            if -1 != stdout.find("%s/%s.git" % (self.git_user, self.git_repo)):
                logging.warn("Not touching existing git repository @ %s" % self.repo_dir)
                return server.repo_dir
    #        else:
    #            raise Exception(stderr)
            os.chdir(self.branch_dir) # return to branch dir
        
        logging.info("Cloning %s/%s.git to %s" % (self.git_user, self.git_repo, server.repo_dir))
        lexec("git clone git@github.com:%s/%s.git %s" % (self.git_user, self.git_repo, os.path.basename(server.repo_dir)))


            
    def select_branch(self, server):
        if server.repo_dir:
            cwd = os.getcwd()
            os.chdir(server.repo_dir)
    
        # Get the current list of branches
        lexec("git fetch")
    
        # List the branches
        (_,stdout,_) = lexec("git branch")
    
        # Branch doesn't exist; create it
        if -1 == stdout.find("%s\n" % self.repo_branch): # note: this is a CRAPPY match!
            logging.info("Connecting to branch %s" % self.repo_branch)
            lexec("git checkout -t origin/%s" % self.repo_branch)
        else:
            logging.info("Changing to branch %s" % self.repo_branch)
            lexec("git checkout %s" % self.repo_branch)
            lexec("git pull origin %s" % self.repo_branch)
        
        # switch directory back
        if repo_dir:
            os.chdir(cwd)
        
        
    def mount(self):

        # Set up central and local servers, in turn
        for key,server in self.servers.items():
            self.setup_repo(server)
            self.select_branch(server)
            server.setup_server()
            server.start_server()



class KaLiteSnapshotProject(KaLiteProject):
    def __init__(self, *args, **kwargs):
        super(KaLiteSnapshotProject, self).__init__(*args, **kwargs)

        self.snapshot_url = None
        self.snapshot_file = None
        self.snapshot_dir = None


    def setup_repo_snapshot(self, server, force_create=False, move_snapshot=False):
        """Set up the specified user's repo as a snapshot--no git history.
        Return the directory it's set up in!"""
    
        if self.git_repo != "ka-lite":
            raise NotImplementedError("Only ka-lite repo has been implemented (repo=%s specified)!" % self.git_repo)
        
        logging.debug("Setting up %s %s %s" % (self.git_user, self.repo_branch, self.git_repo))
    
        # Create the branch directory
        if os.path.exists(self.branch_dir):
            logging.info("Mounting git to existing branch dir: %s" % self.branch_dir)
        else:
            logging.info("Creating branch dir")
            os.makedirs(self.branch_dir)


        os.chdir(self.branch_dir)
    
        # Create a snapshot if we haven't before
        if not self.snapshot_dir:
            force_create = True
            self.snapshot_url  = "https://github.com/%s/%s/archive/%s.zip" % (self.git_user, self.git_repo, self.repo_branch)
            self.snapshot_file = self.branch_dir + "/%s.zip" % self.repo_branch
            self.snapshot_dir  = self.branch_dir + "/%s-%s" % (self.git_repo, self.repo_branch)

        # Need to take a new snapshot
        if os.path.exists(self.snapshot_dir) and force_create:
            shutil.rmtree(self.snapshot_dir)

        # Create the snapshot        
        if os.path.exists(self.snapshot_dir):
            logging.info("Using existing snapshot: %s" % self.snapshot_dir)
        else:
            logging.info("Downloading repo snapshot to %s from %s" % (self.snapshot_file, self.snapshot_url))
            urllib.urlretrieve(self.snapshot_url, self.snapshot_file)
    
            logging.info("Unpacking snapshot to %s" % self.snapshot_dir)
            ZipFile(self.snapshot_file).extractall(self.branch_dir)

            # remove zip file
            os.remove(self.snapshot_file)
            
        # Always redo the server.
        if os.path.exists(server.repo_dir):# and force_create:
            logging.info("Removing old snapshot directory: %s" % server.repo_dir)
            shutil.rmtree(server.repo_dir)

        # Now use the snapshot to create the server directory
#        if os.path.exists(server.repo_dir):
#            logging.info("Leaving existing repo: %s" % server.repo_dir)
#        else:
        if move_snapshot:
            logging.info("Moving snapshot to %s" % server.repo_dir)
            shutil.move(self.snapshot_dir, server.repo_dir)
        else:
            logging.info("Copying snapshot to %s" % server.repo_dir)
            shutil.copytree(self.snapshot_dir, server.repo_dir)

    
    def mount(self):

        # Set up central and local servers, in turn
        #
        # Do this through numeric iteration, so that we
        #   are guaranteed to move the snapshot on the last iteration, 
        #   which is important to save disk space
        #
        nkeys = len(self.servers.keys())
        for i in range(nkeys):#key,server in self.servers.items():
            key = self.servers.keys()[i]
            server = self.servers[key]
            self.setup_repo_snapshot(server, move_snapshot=(i==nkeys-1))
            server.setup_server()
            server.start_server()




def parse_ports(ports):
    """Returns a dict describing the port content"""

    # Port range specified.  
    #  Either get the port from a previous port map, or 
    #  allow the app to randomly choose.
    if -1 != ports.find("-"): # port range
        # default output
        setup_args = { "port_range": map(int,ports.split("-"))}

    # Select specific ports
    elif -1 != ports.find(","): # specific ports
        setup_args = { "open_ports": map(int,ports.split(","))}

    else:
        setup_args = None

    return setup_args


def usage(usage_err=None):
    if usage_err:
        logging.info("ERROR: %s" % usage_err)
    
    logging.info("Usage:")
#    logging.info("\t%s <git_username> <git_branch>", sys.argv[0])
    logging.info("\t%s <git_username> <git_branch> [central or local] [port_range (50-60) or port_list(50,51)", sys.argv[0])
#    logging.info("\t%s <git_username> <git_branch> [repository_name]")
    exit()


if __name__=="__main__":
    logging.getLogger().setLevel(logging.INFO)

    # Get command-line args
    git_user     = sys.argv[1]    if len(sys.argv)>1 else usage("Specify a git account")
    repo_branch  = sys.argv[2]    if len(sys.argv)>2 else usage("Specify a repo branch")
    server_types = sys.argv[3]    if len(sys.argv)>3 else "central,local"
    ports        = sys.argv[4]    if len(sys.argv)>4 else "50000-65000"
    git_repo     = sys.argv[5]    if len(sys.argv)>5 else "ka-lite"

    # Parse the server types and ports
    server_types = server_types.split(",")
    port_arg     = parse_ports(ports)

    # Check/clean up ports
    if not port_arg:
        usage("Could not parse port specification: '%s'" % ports)
    # Gave a list of ports; match them to the list of server types
    if hasattr(port_arg, "open_ports"):
        if len(server_types) != len(port_arg["open_ports"]):
            usage("Port list and server type list must have the same length.")
        port_arg = { "port_map": dict(zip(server_types, port_arg["open_ports"])) }
	
    # Run the project
    kap = KaLiteSnapshotProject(git_user=git_user, repo_branch=repo_branch, git_repo=git_repo, base_dir="/home/ubuntu/ka-lite")
    kap.mount_project(server_types=server_types, **port_arg)
    
    # When in debug mode, there's a lot of output--so output again!
    if logging.getLogger().level>=logging.DEBUG:
        kap.emit_header()
