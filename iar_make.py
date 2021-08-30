#! python3
# -*- coding: utf-8 -*-
#======================================================================
#
# iar_easy_make.py - v1.0.0
#
#======================================================================
import sys, time, os
import configparser


#----------------------------------------------------------------------
# preprocessor: IAR pre build
#----------------------------------------------------------------------
class preprocessor(object):

    # init compiler
    def __init__ (self):
        self.reset()

    # get config
    def preprocess (self, text):
        content = text
        spaces = (' ', '\n', '\t', '\r')
        import io as cStringIO
        srctext = cStringIO.StringIO()
        srctext.write(text)
        srctext.seek(0)
        memo = 0
        i = 0
        length = len(content)
        output = srctext.write
        while i < length:
            char = content[i]
            word = content[i : i + 2]
            if memo == 0:		# text
                if word == '/*':
                    output('``')
                    i += 2
                    memo = 1
                    continue
                if word == '//':
                    output('``')
                    i += 2
                    while (i < len(content)) and (content[i] != '\n'):
                        if content[i] in spaces:
                            output(content[i])
                            i = i + 1
                            continue						
                        output('`')
                        i = i + 1
                    continue
                if char == '\"':
                    output('\"')
                    i += 1
                    memo = 2
                    continue
                if char == '\'':
                    output('\'')
                    i += 1
                    memo = 3
                    continue
                output(char)
            elif memo == 1:		# comments
                if word == '*/':
                    output('``')
                    i += 2
                    memo = 0
                    continue
                if char in spaces:
                    output(content[i])
                    i += 1
                    continue
                output('`')
            elif memo == 2:		# string
                if word == '\\\"':
                    output('$$')
                    i += 2
                    continue
                if word == '\\\\':
                    output('$$')
                    i += 2
                    continue
                if char == '\"':
                    output('\"')
                    i += 1
                    memo = 0
                    continue
                if char in spaces:
                    output(char)
                    i += 1
                    continue
                output('$')
            elif memo == 3:		# chr
                if word == '\\\'':
                    output('$$')
                    i += 2
                    continue
                if word == '\\\\':
                    output('$$')
                    i += 2
                    continue
                if char == '\'':
                    output('\'')
                    i += 1
                    memo = 0
                    continue
                if char in spaces:
                    output(char)
                    i += 1
                    continue
                output('$')
            i += 1
        srctext.truncate()
        return srctext.getvalue()

    # filter
    def cleanup_memo (self, text):
        content = text
        outtext = ''
        srctext = self.preprocess(content)
        space = ( ' ', '\t', '`' )
        start = 0
        endup = -1
        sized = len(srctext)
        while (start >= 0) and (start < sized):
            start = endup + 1
            endup = srctext.find('\n', start)
            if endup < 0:
                endup = sized
            empty = 1
            memod = 0
            for i in range(start, endup):
                if not (srctext[i] in space):
                    empty = 0
                if srctext[i] == '`':
                    memod = 1
            if empty and memod:
                continue
            for i in range(start, endup):
                if srctext[i] != '`':
                    outtext = outtext + content[i]
            outtext = outtext + '\n'
        return outtext

    # reset depedence
    def reset (self):
        self._references = {}
        return 0


#----------------------------------------------------------------------
# execute and capture
#----------------------------------------------------------------------
def execute(args, shell = False, capture = False):
    import sys, os
    parameters = []
    if type(args) in (type(''), type(u'')):
        import shlex
        cmd = args
        if sys.platform[:3] == 'win':
            ucs = False
            args = shlex.split(cmd.replace('\\', '\x00'))
            args = [ n.replace('\x00', '\\') for n in args ]
            if ucs:
                args = [ n.decode('utf-8') for n in args ]
        else:
            args = shlex.split(cmd)
    for n in args:
        if sys.platform[:3] != 'win':
            replace = { ' ':'\\ ', '\\':'\\\\', '\"':'\\\"', '\t':'\\t', \
                '\n':'\\n', '\r':'\\r' }
            text = ''.join([ replace.get(ch, ch) for ch in n ])
            parameters.append(text)
        else:
            if (' ' in n) or ('\t' in n) or ('"' in n): 
                parameters.append('"%s"'%(n.replace('"', ' ')))
            else:
                parameters.append(n)
    cmd = ' '.join(parameters)
    if sys.platform[:3] == 'win' and len(cmd) > 255:
        shell = False
    if shell and (not capture):
        os.system(cmd)
        return ''
    import subprocess
    if 'Popen' in subprocess.__dict__:
        if sys.platform[:3] != 'win' and shell:
            p = None
            stdin, stdouterr = os.popen4(cmd)
        else:
            p = subprocess.Popen(args, shell = shell,
                    stdin = subprocess.PIPE, stdout = subprocess.PIPE, 
                    stderr = subprocess.STDOUT)
            stdin, stdouterr = (p.stdin, p.stdout)
    else:
        p = None
        stdin, stdouterr = os.popen4(cmd)
    text = stdouterr.read()
    stdin.close()
    stdouterr.close()
    if p: p.wait()
    if not capture:
        sys.stdout.write(text)
        sys.stdout.flush()
        return ''
    return text


#----------------------------------------------------------------------
# Default CFG File
#----------------------------------------------------------------------
ININAME = ''
INIPATH = 'iar_make.ini'

CFG = {'abspath':False, 'verbose':False, 'silent':False}


#----------------------------------------------------------------------
# configure: get gcc read config
#----------------------------------------------------------------------
class configure(object):

    # init
    def __init__ (self, ininame = ''):
        self.dirpath = os.path.split(os.path.abspath(__file__))[0]
        self.current = os.getcwd()
        if not ininame:
            ininame = ININAME and ININAME or 'iar_make.ini'
        self.ininame = ininame
        self.inipath = os.path.join(self.dirpath, self.ininame)
        self.haveini = False
        self.dirhome = ''
        self.target = ''
        self.config = {}
        self.cp = configparser.ConfigParser()
        self.searchdirs = None
        self.environ = {}
        self.exename = {}
        self.replace = {}
        for n in os.environ:
            self.environ[n] = os.environ[n]
        if sys.platform[:3] == 'win':
            self.GetShortPathName = None
        self.cpus = 0
        self.inited = False
        self.fpic = 0
        self.name = {}
        ext = ('.c', '.cpp', '.c', '.cxx', '.s', '.asm')
        self.extnames = ext
        self.__jdk_home = None
        self.reset()

    # reset config
    def reset (self):
        self.inc = {}		# include
        self.lib = {}		# lib 
        self.flag = {}		# flag
        self.pdef = {}		# pdef
        self.link = {}		# link
        self.param_build = ''
        self.param_compile = ''
        return 0

    # macros
    def _expand (self, section, environ, item, d = 0):
        if not environ: environ = {}
        if not section: section = {}
        text = ''
        if item in environ:
            text = environ[item]
        if item in section:
            text = section[item]
        if d >= 20: return text
        names = {}
        index = 0
        while 1:
            index = text.find('$(', index)
            if index < 0: break
            p2 = text.find(')', index)
            if p2 < 0: break
            name = text[index + 2:p2]
            index = p2 + 1
            names[name] = name.upper()
        for name in names:
            if name != item:
                value = self._expand(section, environ, name.upper(), d + 1)
            elif name in environ:
                value = environ[name]
            else:
                value = ''
            text = text.replace('$(' + name + ')', value)
            names[name] = value
        return text

    # read ini
    def _readini (self, inipath):
        self.cp = configparser.ConfigParser()
        if os.path.exists(inipath):
            self.iniload = os.path.abspath(inipath)
            config = {}
            try: self.cp.read(inipath)
            except: pass
            for sect in self.cp.sections():
                for key, val in self.cp.items(sect):
                    lowsect, lowkey = sect.lower(), key.lower()
                    self.config.setdefault(lowsect, {})[lowkey] = val
                    config.setdefault(lowsect, {})[lowkey] = val
            self.config['default'] = self.config.get('default', {})
            config['default'] = config.get('default', {})
            inihome = os.path.abspath(os.path.split(inipath)[0])
            for exename in ('gcc', 'tc_link', 'ld', 'ar', 'as'):
                if not exename in config['default']:
                    continue
                self.exename[exename] = config['default'][exename]
            for bp in ('include', 'lib'):
                if not bp in config['default']:
                    continue
                data = []
                for n in config['default'][bp].replace(';', ',').split(','):
                    n = os.path.normpath(os.path.join(inihome, self.pathconf(n)))
                    n = n.replace('\\', '/')
                    data.append("'" + n + "'")
                text = ','.join(data)
                config['default'][bp] = text
                self.config['default'][bp] = text
            java = config['default'].get('java', '')
            if java:
                java = os.path.join(inihome, java)
                if not os.path.exists(java):
                    sys.stderr.write('error: %s: %s not exists\n'%(inipath, java))
                    sys.stderr.flush()
                else:
                    self.config['default']['java'] = os.path.abspath(java)
            self.haveini = True
        return 0

    def init (self):
        if self.inited:
            return 0
        self.config = {}
        self.reset()
        fn = INIPATH
        self.iniload = os.path.abspath(self.inipath)
        if fn:
            if os.path.exists(fn):
                self._readini(fn)
                self.iniload = os.path.abspath(fn)
            else:
                sys.stderr.write('error: cannot open %s\n'%fn)
                sys.stderr.flush()
                sys.exit(1)
        if not self.haveini:
            sys.stderr.flush()
        defined = self.exename.get('gcc', None) and True or False
        for name in ('gcc', 'tc_link', 'ar', 'ld', 'as'):
            exename = self.exename.get(name, name)
            elements = list(os.path.splitext(exename)) + ['', '']
            if not elements[1]: exename = elements[0] + '.exe'
            self.exename[name] = exename
        gcc = self.exename['gcc']
        p1 = os.path.join(self.dirhome, '%s.exe'%gcc)
        p2 = os.path.join(self.dirhome, '%s'%gcc)
        if (not os.path.exists(p1)) and (not os.path.exists(p2)):
            self.dirhome = ''
        if sys.platform[:3] != 'win':
            if self.dirhome[1:2] == ':':
                self.dirhome = ''
        if self.dirhome:
            self.dirhome = os.path.abspath(self.dirhome)
        try: 
            cpus = self._getitem('default', 'cpu', '')
            intval = int(cpus)
            self.cpus = intval
        except:
            pass
        self.name = {}
        self.name[sys.platform.lower()] = 1
        if sys.platform[:3] == 'win':
            self.name['win'] = 1
        if sys.platform[:5] == 'linux':
            self.name['linux'] = 1
        if 'win' in self.name:
            self.name['nt'] = 1
        self.target = self._getitem('default', 'target')
        names = self._getitem('default', 'name')
        if names:
            self.name = {}
            for name in names.replace(';', ',').split(','):
                name = name.strip('\r\n\t ').lower()
                if not name: continue
                self.name[name] = 1
                if not self.target:
                    self.target = name
        if not self.target:
            self.target = sys.platform
        self.target = self.target.strip('\r\n\t ')
        if sys.platform[:3] in ('win'):
            self.fpic = False
        else:
            self.fpic = True
        #self.__python_config()
        self.replace = {}
        self.replace['home'] = self.dirhome
        self.replace['iarmake'] = self.dirpath
        self.replace['inihome'] = os.path.dirname(self.iniload)
        self.replace['inipath'] = self.inipath
        self.replace['target'] = self.target
        self.inited = True
        return 0

    # read config
    def _getitem (self, sect, key, default = ''):
        return self.config.get(sect, {}).get(key, default)

    # get path valid
    def path (self, path):
        text = ''
        issep = False
        for n in path:
            if n == '/':
                if issep == False: text += n
                issep = True
            else:
                text += n
                issep = False
        return os.path.abspath(text)

    def pathtext (self, name):
        name = os.path.normpath(name)
        name = name.replace('"', '""')
        if ' ' in name:
            return '"%s"'%(name)
        return name

    # path true
    def pathrel (self, name, start = None):
        return name

    # push inc
    def push_inc (self, inc):
        path = self.path(inc)
        if not os.path.exists(path):
            sys.stderr.write('warning: ignore invalid path %s\n'%path)
            return -1
        self.inc[path] = 1
        return 0

    # push lib
    def push_lib (self, lib):
        path = self.path(lib)
        if not os.path.exists(path):
            sys.stderr.write('warning: ignore invalid path %s\n'%path)
            return -1
        self.lib[path] = 1
        return 0

    # push compile flag
    def push_flag (self, flag):
        if not flag in self.flag:
            self.flag[flag] = len(self.flag)
        return 0

    # macros
    def push_pdef (self, define):
        self.pdef[define] = 1

    # config path
    def pathconf (self, path):
        path = path.strip(' \t\r\n')
        if path[:1] == '\'' and path[-1:] == '\'': path = path[1:-1]
        if path[:1] == '\"' and path[-1:] == '\"': path = path[1:-1]
        return path.strip(' \r\n\t')

    # refresh configuration
    def loadcfg (self, sect = 'default', reset = True):
        self.init()
        if reset: self.reset()
        f1 = lambda n: (n[:1] != '\'' or n[-1:] != '\'') and n
        config = lambda n: self._getitem(sect, n, '')
        for path in config('include').replace(';', ',').split(','):
            path = self.pathconf(path)
            if not path: continue
            self.push_inc(path)
        for path in config('lib').replace(';', ',').split(','):
            path = self.pathconf(path)
            if not path: continue
            self.push_lib(path)
        for flag in config('flag').replace(';', ',').split(','):
            flag = flag.strip(' \t\r\n')
            if not flag: continue
            self.push_flag(flag)
        for pdef in config('define').replace(';', ',').split(','):
            pdef = pdef.strip(' \t\r\n')
            if not pdef: continue
            self.push_pdef(pdef.replace(' ', '_'))
        for name in ('cflag', 'cxxflag', 'mflag', 'mmflag', 'sflag'):
            for flag in config(name).replace(';', ',').split(','):
                flag = flag.strip(' \t\r\n')
                if not flag: continue
                self.push_cond(flag, name)
        self.parameters()
        return 0

    # return config dict value
    def sequence (self, data):
        x = [ (n, k) for (k, n) in data.items() ]
        x.sort()
        y = [ n for (k, n) in x ]
        return y

    # replace key 
    def __replace_key (self, text):
        for key in self.replace:
            value = self.replace[key]
            check = '$(' + key + ')'
            if check in text:
                text = text.replace(check, value)
        return text

    # return parameter	
    def parameters (self):
        text = ''
        for inc in self.sequence(self.inc):
            text += '-I%s '%inc
        for lib in self.sequence(self.lib):
            text += '-L%s '%lib
        for flag in self.sequence(self.flag):
            text += '%s '%self.__replace_key(flag)
        for pdef in self.sequence(self.pdef):
            text += '-D%s '%pdef
        self.param_compile = text.strip(' ')
        text = ''
        for link in self.sequence(self.link):
            text += '%s '%self.__replace_key(link)
        self.param_build = self.param_compile + ' ' + text
        return text


    # run toolchain
    def execute (self, binname, parameters, printcmd = False, capture = False):
        path = binname
        cmd = ( '%s %s'%(path, parameters) ).replace('\\','/')
        text = ''
        if printcmd:
            print (cmd)
        '''
        sys.stdout.flush()
        sys.stderr.flush()
        '''
        ret = os.system(cmd)
        return ret
        #text = text + str(execute(cmd, shell = False, capture = True))
        #return text

    # run gcc
    def gcc (self, parameters, needlink, printcmd = False, capture = False):
        param = self.param_build
        if not needlink:
            param = self.param_compile
        parameters = '%s %s'%(param, parameters)
        #${TC_CC} ${SRCFILE} ${GCCFLAGS}  -o $@
        return self.execute(self.exename['gcc'], parameters, printcmd, capture)

    # run tc_link
    def tc_link (self, parameters, needlink, printcmd = False, capture = False):
        param = self.param_build
        if not needlink:
            param = self.param_compile
        parameters = '%s %s'%(parameters, param)
        return self.execute(self.exename['tc_link'], parameters, printcmd, capture)

    # call link
    def link (self, parameters, printcmd = False, capture = False):
        param = self.param_build
        parameters = '%s %s'%(parameters, param)
        return self.execute(self.exename['gcc'], parameters, printcmd, capture)

    # compile
    def compile (self, srcname, objname, cflags, printcmd = False, capture = False):
        srcname = self.pathrel(srcname)
        cmd = '%s -o %s %s'%(srcname, self.pathrel(objname), cflags)

        extname = os.path.splitext(srcname)[-1].lower()
        printcmd = False
        return self.gcc(cmd, False, printcmd, capture)


    # make library
    def makelib (self, output, objs = [], printcmd = False, capture = False):
        if 0:
            name = ' '.join([ self.pathrel(n) for n in objs ])
            parameters = '%s %s'%(self.pathrel(output), name)
            return self.execute(self.exename['ar'], parameters, printcmd, capture)
        objs = [ n for n in objs ]
        return self.composite(output, objs, printcmd, capture)

    # create app
    def makeapp (self):
        return 

    # combine .o to .a
    def composite (self, output, objs = [], printcmd = False, capture = False):
        import os, tempfile, shutil
        cwd = os.getcwd()
        temp = tempfile.mkdtemp('.int', 'lib')
        output = os.path.abspath(output)
        libname = []
        for name in [ os.path.abspath(n) for n in objs ]:
            if not name in libname:
                libname.append(name)
        names = {}
        for source in libname:
            files = []
            filetype = os.path.splitext(source)[-1].lower()
            if filetype == '.o':
                files.append(source)
            else:
                args = '-x %s'%self.pathrel(source)
                self.execute(self.exename['ar'], args, printcmd, capture)
                for fn in os.listdir('.'):
                    files.append(os.path.abspath(fn))
            for fn in files:
                name = fn
                last = None
                for i in range(1000):
                    newname = (i > 0) and (part[0] + '_%d'%i + part[1]) or name
                    if not newname in names:
                        last = newname
                        names[last] = 1
                        break
        args = []
        args = ' '.join(args + [n for n in names])
        args+= ' --create -o '
        args+= output
        try: os.remove(output)
        except: pass
        printcmd = True
        self.execute(self.exename['ar'], args, printcmd, capture)
        os.chdir(cwd)
        shutil.rmtree(temp)
        return 0


#----------------------------------------------------------------------
# coremake: core make
#----------------------------------------------------------------------
class coremake(object):
    def __init__ (self, ininame = ''):
        self.ininame = ininame
        self.config = configure(self.ininame)
        self.inited = 0
        self.extnames = self.config.extnames
        self.envos = {}
        for k, v in os.environ.items():
            self.envos[k] = v
        self.reset()

    # reset config
    def reset (self):
        self.config.reset()
        self._out = ''		# target
        self._int = ''		# object file
        self._main = ''		# .mk
        self._mode = 'exe'	# exe lib
        self._src = []		# src
        self._obj = []		# obj
        self._opt = []
        self._environ = {}	# env
        self.inited = 0
        
    # init file name
    def init (self, main, out = 'a.out', mode = 'exe', intermediate = ''):
        if not mode in ('exe', 'lib'):
            raise Exception("mode must in ('exe', 'lib')")
        self.reset()
        self.config.init()
        self.config.loadcfg()
        self._main = os.path.abspath(main)
        self._mode = mode
        self._out = os.path.abspath(out)
        self._int = intermediate
        self._out = self.outname(self._out, mode)

    # get obj name from source file
    def objname (self, srcname, intermediate = ''):
        part = os.path.splitext(srcname)
        ext = part[1].lower()
        if ext in self.extnames:
            if intermediate:
                name = os.path.join(intermediate, os.path.split(part[0])[-1])
                name = os.path.abspath(name + '.o')
            else:
                name = os.path.abspath(part[0] + '.o')
            return name
        if not ext in ('.o', '.obj'):
            raise Exception('unknow ext-type of %s\n'%srcname)
        return srcname

    # get target
    def outname (self, output, mode = 'exe'):
        if not mode in ('exe', 'lib'):
            raise Exception("mode must in ('exe', 'lib')")
        part = os.path.splitext(os.path.abspath(output))
        output = part[0]
        if mode == 'exe':
            output += '.exe'
        elif mode == 'lib':
            if not part[1]: output += '.a'
            else: output += part[1]
        return output

    # get obj file list
    def scan (self, sources, intermediate = ''):
        src2obj = {}
        obj2src = {}
        for src in sources:
            obj = self.objname(src, intermediate)
            if obj in obj2src:
                p1, p2 = os.path.splitext(obj)
                index = 1
                while True:
                    name = '%s%d%s'%(p1, index, p2)
                    if not name in obj2src:
                        obj = name
                        break
                    index += 1
            src2obj[src] = obj
            obj2src[obj] = src
        obj2src = None
        return src2obj

    # add source file and obj file
    def push (self, srcname, objname, options):
        self._src.append(os.path.abspath(srcname))
        self._obj.append(os.path.abspath(objname))
        self._opt.append(options)

    def mkdir (self, path):
        path = os.path.abspath(path)
        if os.path.exists(path):
            return 0
        name = ''
        part = os.path.abspath(path).replace('\\', '/').split('/')
        if (path[1:2] == ':'):
            part[0] += '/'
        for n in part:
            name = os.path.abspath(os.path.join(name, n))
            if not os.path.exists(name):
                os.mkdir(name)
        return 0

    def remove (self, path):
        try: os.remove(path)
        except: pass
        if os.path.exists(path):
            sys.stderr.write('error: cannot remove \'%s\'\n'%path)
            sys.stderr.flush()
            sys.exit(0)
        return 0

    # compile by one thread
    def _compile_single (self, skipexist, printmode, printcmd):
        retval = 0
        for i in range(len(self._src)):
            srcname = self._src[i]
            objname = self._obj[i]
            options = self._opt[i]
            if srcname == objname:
                continue
            if skipexist and os.path.exists(objname):
                continue
            try: os.remove(os.path.abspath(objname))
            except: pass
            if printmode & 1:
                name = self.config.pathrel(srcname)
                if name[:1] == '"':
                    name = name[1:-1]
                if CFG['abspath']:
                    name = os.path.abspath(srcname)
            self.config.compile(srcname, objname, options, printcmd)
            if not os.path.exists(objname):
                retval = -1
                break
        return retval

    # compile by multi thread
    def _compile_threading (self, skipexist, printmode, printcmd, cpus):
        # compile by time
        ctasks = [ (os.path.getsize(s), s, o, t) for s, o, t in zip(self._src, self._obj, self._opt) ]
        ctasks.sort()
        import threading
        self._task_lock = threading.Lock()
        self._task_retval = 0
        self._task_finish = False
        self._task_queue = ctasks
        self._task_thread = []
        self._task_error = ''
        for n in range(cpus):
            parameters = (skipexist, printmode, printcmd, cpus - 1 - n)
            th = threading.Thread(target = self._compile_working_thread, args = parameters)
            self._task_thread.append(th)
        for th in self._task_thread:
            th.start()
        for th in self._task_thread:
            th.join()
        self._task_thread = None
        self._task_lock = None
        self._task_queue = None
        for objname in self._obj:
            if not os.path.exists(objname):
                self._task_retval = -1
                break
        return self._task_retval

    # compile thread
    def _compile_working_thread (self, skipexist, printmode, printcmd, id):
        mutex = self._task_lock
        while True:
            weight, srcname, objname = 0, '', ''
            mutex.acquire()
            if self._task_finish:
                mutex.release()
                break
            if not self._task_queue:
                mutex.release()
                break
            weight, srcname, objname, options = self._task_queue.pop()
            mutex.release()
            if srcname == objname:
                continue
            if skipexist and os.path.exists(objname):
                continue
            try: os.remove(os.path.abspath(objname))
            except: pass
            timeslap = time.time()
            output = self.config.compile(srcname, objname, options, printcmd, True)
            timeslap = time.time() - timeslap
            result = True
            if not os.path.exists(objname):
                mutex.acquire()
                self._task_retval = -1
                self._task_finish = True
                mutex.release()
                result = False
            mutex.acquire()
            if printmode & 1:
                name = self.config.pathrel(srcname)
                if name[:1] == '"':
                    name = name[1:-1]
                if CFG['abspath']:
                    name = os.path.abspath(srcname)
                sys.stdout.write(name + '\n')
            if sys.platform[:3] == 'win':
                pass
            sys.stdout.write('next')
            sys.stdout.flush()
            mutex.release()
            time.sleep(0.01)
        return 0

    # compile file
    def compile (self, skipexist = False, printmode = 0, cpus = 0):
        self.mkdir(os.path.abspath(self._int))
        printcmd = False
        if printmode & 4:
            printcmd = True
        if printmode & 2:
            print ('compiling ...')
        t = time.time()
        if cpus <= 1:
            retval = self._compile_single(skipexist, printmode, printcmd)
        else:
            retval = self._compile_threading(skipexist, printmode, printcmd, cpus)
        t = time.time() - t
        return retval

    # link
    def link (self, skipexist = False, printmode = 0):
        retval = 0
        printcmd = False
        if printmode & 4:
            printcmd = True
        if printmode & 2:
            print ('linking ...')
        output = self._out
        if skipexist and os.path.exists(output):
            return output
        self.remove(output)
        self.mkdir(os.path.split(output)[0])
        if self._mode == 'lib':
            self.config.makelib(output, self._obj, printcmd)
        if not os.path.exists(output):
            return ''
        return output


    def event (self, scripts):
        pass

    # build
    def build (self, skipexist = False, printmode = 0):
        if self.compile(skipexist, printmode) != 0:
            return -1
        output = self.link(skipexist, printmode)
        if output == '':
            return -2
        return output



#----------------------------------------------------------------------
# iparser: parse config message
#----------------------------------------------------------------------
class iparser (object):
    def __init__ (self, ininame = ''):
        self.preprocessor = preprocessor()
        self.coremake = coremake(ininame)
        self.config = self.coremake.config
        self.extnames = self.config.extnames
        self.reset()

    # config reset TODO:
    def reset (self):
        self.src = []
        self.inc = []
        self.lib = []
        self.imp = []
        self.exp = []
        self.link = []
        self.flag = []
        self.environ = {}
        self.events = {}
        self.mode = 'exe'
        self.define = {}
        self.name = ''
        self.home = ''
        self.out = ''
        self.int = ''
        self.makefile = ''
        self.incdict = {}
        self.libdict = {}
        self.srcdict = {}
        self.optdict = {}
        self.makefile = ''

    # obj name
    def __getitem__ (self, key):
        return self.srcdict[key]

    # __iter__
    def __iter__ (self):
        return self.src.__iter__()

    # add source file
    def push_src (self, filename, options):
        filename = os.path.abspath(filename)
        realname = os.path.normcase(filename)
        if filename in self.srcdict:	
            return -1
        self.srcdict[filename] = ''
        self.optdict[filename] = options
        self.src.append(filename)
        return 0


    # add include path
    def push_inc (self, inc):
        if inc in self.incdict:
            return -1
        self.incdict[inc] = len(self.inc)
        self.inc.append(inc)
        return 0

    # add lib
    def push_lib (self, lib):
        if lib in self.libdict:
            return -1
        self.libdict[lib] = len(self.lib)
        self.lib.append(lib)
        return 0


    # add macro
    def push_define (self, define, value = 1):
        self.define[define] = value
        return 0

    # parse start
    def parse (self, makefile):
        self.reset()
        self.config.init()
        makefile = os.path.abspath(makefile)
        self.makefile = makefile
        part = os.path.split(makefile)
        self.home = part[0]
        self.name = os.path.splitext(part[1])[0]
        if not os.path.exists(makefile):
            sys.stderr.write('error: %s cannot be open\n'%(makefile))
            sys.stderr.flush()
            return -1
        cfg = self.config.config.get('default', {})
        extname = os.path.splitext(makefile)[1].lower()
        if extname in ('.mk', '.py'):
            if self.scan_makefile() != 0:
                return -3
        else:
            sys.stderr.write('error: unknow file type of "%s"\n'%makefile)
            sys.stderr.flush()
            return -5
        if not self.out:
            self.out = os.path.splitext(makefile)[0]
        self.out = self.coremake.outname(self.out, self.mode)
        self._update_obj_names()
        return 0

    # get relative path
    def pathrel (self, name, current = ''):
        if not current:
            current = os.getcwd()
        current = current.replace('\\', '/')
        if len(current) > 0:
            if current[-1] != '/':
                current += '/'
        name = self.path(name).replace('\\', '/')
        size = len(current)
        if name[:size] == current:
            name = name[size:]
        return name

    # config path
    def pathconf (self, path):
        path = path.strip(' \r\n\t')
        if path[:1] == '\'' and path[-1:] == '\'': path = path[1:-1]
        if path[:1] == '\"' and path[-1:] == '\"': path = path[1:-1]
        return path.strip(' \r\n\t')

    # scan project file
    def scan_makefile (self):
        savedir = os.getcwd()
        os.chdir(os.path.split(self.makefile)[0])
        ext = os.path.splitext(self.makefile)[1].lower()
        lineno = 1
        retval = 0
        for text in open(self.makefile, 'r'):
            if ext in ('.py'):
                text = text.strip('\r\n\t ')
                if text[:3] != '##!':
                    continue
                text = text[3:]
            if self._process(self.makefile, lineno, text) != 0:
                retval = -1
                break
            lineno += 1
        os.chdir(savedir)
        return retval

    # print error
    def error (self, text, fname = '', line = -1):
        message = ''
        if fname and line > 0:
            message = '%s:%d: '%(fname, line)
        sys.stderr.write(message + text + '\n')
        sys.stderr.flush()
        return 0

    # src handle
    def _process_src (self, textline, fname = '', lineno = -1):
        ext1 = ('.c', '.cpp', '.cxx', '.asm')
        ext2 = ('.s', '.o', '.obj')
        pos = textline.find(':')
        body, options = textline, ''
        pos = textline.find(':')
        if pos >= 0:
            split = (sys.platform[:3] != 'win') and True or False
            if sys.platform[:3] == 'win':
                if not textline[pos:pos + 2] in (':/', ':\\'):
                    split = True
            if split:
                body = textline[:pos].strip('\r\n\t ')
                options = textline[pos + 1:].strip('\r\n\t ')
        for name in body.replace(';', ',').split(','):
            srcname = self.pathconf(name)
            if not srcname:
                continue
            if (not '*' in srcname) and (not '?' in srcname):
                names = [ srcname ]
            else:
                import glob
                names = glob.glob(srcname)
            for srcname in names:
                absname = os.path.abspath(srcname)
                if not os.path.exists(absname):
                    self.error('error: %s: No such file'%srcname, \
                        fname, lineno)
                    return -1
                extname = os.path.splitext(absname)[1].lower()
                if (not extname in ext1) and (not extname in ext2):
                    self.error('error: %s: Unknow file type'%absname, \
                        fname, lineno)
                    return -2
                self.push_src(absname, options)
        return 0

    # parse message
    def _process (self, fname, lineno, text):
        text = text.strip(' \t\r\n')
        if not text:					# space
            return 0
        if text[:1] in (';', '#'):		# skip commont
            return 0
        pos = text.find(':')
        if pos < 0:
            self.error('unknow make command', fname, lineno)
            return -1
        command, body = text[:pos].lower(), text[pos + 1:]
        pos = command.find('/')
        if pos >= 0:
            condition, command = command[:pos].lower(), command[pos + 1:]
            match = False
            if not match:
                return 0
        environ = {}
        environ['target'] = self.config.target
        environ['int'] = self.int
        environ['out'] = self.out
        environ['mode'] = self.mode
        environ['home'] = os.path.dirname(os.path.abspath(fname))
        environ['bin'] = self.config.dirhome
        for name in ('gcc', 'tc_link', 'ar', 'ld', 'as'):
            if name in self.config.exename:
                data = self.config.exename[name]
                environ[name] = os.path.join(self.config.dirhome, data)
        environ['cc'] = environ['gcc']
        for name in environ:
            key = '$(%s)'%name
            val = environ[name]
            if key in body:
                body = body.replace(key, val)
        if command in ('out', 'output'):
            self.out = os.path.abspath(self.pathconf(body))
            return 0
        if command in ('int', 'intermediate'):
            self.int = os.path.abspath(self.pathconf(body))
            return 0
        if command in ('src', 'source'):
            retval = self._process_src(body, fname, lineno)
            return retval
        if command in ('mode', 'mod'):
            body = body.lower().strip(' \r\n\t')
            if not body in ('exe', 'lib'):
                self.error('error: %s: mode is not supported'%body, \
                    fname, lineno)
                return -1
            self.mode = body
            return 0
        if command in ('inc', 'lib'):
            for name in body.replace(';', ',').split(','):
                srcname = self.pathconf(name)
                if not srcname:
                    continue
                absname = os.path.abspath(srcname)
                if not os.path.exists(absname):
                    self.error('error: %s: No such directory'%srcname, \
                        fname, lineno)
                    return -1
                if command == 'inc': 
                    self.push_inc(absname)
                elif command == 'lib':
                    self.push_lib(absname)
            return 0
        if command == 'flag':
            for name in body.replace(';', ',').split(','):
                srcname = self.pathconf(name)
                if not srcname:
                    continue
                if srcname[:2] in ('-o', '-I', '-B', '-L'):
                    self.error('error: %s: invalid option'%srcname, \
                        fname, lineno)
                self.push_flag(srcname)
            return 0
        if command in ('argcc', 'ac'):
            self.push_flag(body.strip('\r\n\t '))
            return 0
        if command == 'define':
            for name in body.replace(';', ',').split(','):
                srcname = self.pathconf(name).replace(' ', '_')
                if not srcname:
                    continue
                self.push_define(srcname)
            return 0
        self.error('error: %s: invalid command'%command, fname, lineno)
        return -1

    # detect obj
    def _update_obj_names (self):
        src2obj = self.coremake.scan(self.src, self.int)
        for fn in self.src:
            obj = src2obj[fn]
            self.srcdict[fn] = os.path.abspath(obj)
        return 0

#----------------------------------------------------------------------
# dependence: Compile/Link/Build
#----------------------------------------------------------------------
class dependence (object):

    def __init__ (self, parser = None):
        self.parser = parser
        self.preprocessor = preprocessor()
        self.reset()

    def reset (self):
        self._mtime = {}
        self._dirty = {}
        self._depinfo = {}
        self._depname = ''
        self._outchg = False

    def mtime (self, fname):
        fname = os.path.abspath(fname)
        if fname in self._mtime:
            return self._mtime[fname]
        try: mtime = os.path.getmtime(fname)
        except: mtime = 0.0
        mtime = float('%.6f'%mtime)
        self._mtime[fname] = mtime
        return mtime

    def _scan_src (self, srcname):
        srcname = os.path.abspath(srcname)
        if not srcname in self.parser:
            return None
        if not os.path.exists(srcname):
            return None
        objname = self.parser[srcname]
        head, lost, src = self.preprocessor.dependence(srcname)
        filelist = [srcname] + head
        dependence = []
        for fn in filelist:
            name = os.path.abspath(fn)
            dependence.append((name, self.mtime(name)))
        return dependence

    def _update_dep (self, srcname):
        srcname = os.path.abspath(srcname)
        if not srcname in self.parser:
            return -1
        retval = 0
        debug = 0
        if debug: print ('\n<dep:%s>'%srcname)
        objname = self.parser[srcname]
        srctime = self.mtime(srcname)
        objtime = self.mtime(objname)
        update = False
        info = self._depinfo.setdefault(srcname, {})
        #info = srcname
        if len(info) == 0: 
            update = True
        if not update:
            for fn in info:
                if not os.path.exists(fn):
                    update = True
                    break
                oldtime = info[fn]
                newtime = self.mtime(fn)
                if newtime > oldtime:
                    update = True
                    break
        info = self._depinfo[srcname]
        for fn in info:
            oldtime = info[fn]
            if oldtime > objtime:
                self._dirty[srcname] = 1
                retval = 1
                break
        if debug: print ('</dep:%s>\n'%srcname)
        return retval

    def _load_dep (self):
        lineno = -1
        retval = 0
        if os.path.exists(self._depname):
            for line in open(self._depname, 'r'):
                line = line.strip(' \t\r\n')
                if not line: continue
                pos = line.find('=')
                if pos < 0: continue
                src, body = line[:pos], line[pos + 1:]
                src = os.path.abspath(src)
                if not os.path.exists(src): continue
                item = body.replace(';', ',').split(',')
                count = len(item) / 2
                info = {}
                self._depinfo[src] = info
                for i in range(int(count)):
                    fname = item[i * 2 + 0].strip(' \r\n\t')
                    mtime = item[i * 2 + 1].strip(' \r\n\t')
                    fname = self.parser.pathconf(fname)
                    info[fname] = float(mtime)
            retval = 0
        for fn in self.parser:
            self._update_dep(fn)
        return retval

    def _save_dep (self):
        path = os.path.split(self._depname)[0]
        if not os.path.exists(path):
            self.parser.coremake.mkdir(path)
        fp = open(self._depname, 'w')
        names = self._depinfo.keys()
        # names.sort()
        sorted(names)
        for src in names:
            info = self._depinfo[src]
            fp.write('%s = '%(src))
            part = []
            keys = info.keys()
            # keys.sort()
            sorted(keys)
            for fname in keys:
                mtime = info[fname]
                if ' ' in fname: fname = '"%s"'%fname
                part.append('%s, %.6f'%(fname, mtime))
            fp.write(', '.join(part) + '\n')
        fp.close()
        return 0

    def process (self):
        self.reset()
        parser = self.parser
        depname = parser.name + '.p'
        self._depname = os.path.join(parser.home, depname)
        if parser.int:
            self._depname = os.path.join(parser.int, depname)
        self._depname = os.path.abspath(self._depname)
        self._load_dep()
        self._save_dep()
        return 0


#----------------------------------------------------------------------
# iar_make: Compile/Link/Build
#----------------------------------------------------------------------
class iar_make (object):

    def __init__ (self, ininame = ''):
        if ininame == '': ininame = 'iar_make.ini'
        self.parser = iparser(ininame)
        self.coremake = self.parser.coremake
        self.dependence = dependence(self.parser)
        self.config = self.coremake.config
        self.cpus = -1
        self.loaded = 0

    def reset (self):
        self.parser.reset()
        self.coremake.reset()
        self.dependence.reset()
        self.loaded = 0

    def open (self, makefile):
        self.reset()
        self.config.init()
        environ = {}
        cfg = self.config.config
        if 'environ' in cfg:
            for k, v in cfg['environ'].items():
                environ[k.upper()] = v
        retval = self.parser.parse(makefile)
        if retval != 0:
            return -1
        parser = self.parser
        self.coremake.init(makefile, parser.out, parser.mode, parser.int)
        for src in self.parser:
            obj = self.parser[src]
            opt = self.parser.optdict[src]
            self.coremake.push(src, obj, opt)
        savedir = os.getcwd()
        os.chdir(os.path.dirname(os.path.abspath(makefile)))
        hr = self._config()
        os.chdir(savedir)
        if hr != 0:
            return -2
        self.coremake._environ = {}
        for k, v in environ.items():
            self.coremake._environ[k] = v
        for k, v in self.parser.environ.items():
            self.coremake._environ[k] = v

        for key,value in self.coremake._environ.items():
            print(key+':'+value)

        self.dependence.process()
        self.loaded = 1
        return 0

    def _config (self):
        self.config.replace['makefile'] = self.coremake._main
        self.config.replace['workspace'] = os.path.dirname(self.coremake._main)
        for name, fname, lineno in self.parser.imp:
            if not name in self.config.config:
                self.parser.error('error: %s: No such config section'%name, \
                    fname, lineno)
                return -1
            self.config.loadcfg(name, True)
        for inc in self.parser.inc:
            self.config.push_inc(inc)
        for lib in self.parser.lib:
            self.config.push_lib(lib)
        for flag in self.parser.flag:
            self.config.push_flag(flag)
        for pdef in self.parser.define:
            self.config.push_pdef(pdef)
        self.config.parameters()
        return 0

    def compile (self, printmode = 0):
        if not self.loaded:
            return 1
        for src in self.parser:
            if src in self.dependence._dirty:
                obj = self.parser[src]
                if obj != src:
                    self.coremake.remove(obj)
        cpus = self.config.cpus
        if self.cpus >= 0:
            cpus = self.cpus
        retval = self.coremake.compile(True, printmode, cpus)
        if retval != 0:
            return 2
        return 0

    def link (self, printmode = 0):
        if not self.loaded:
            return 1
        update = False
        outname = self.parser.out
        outtime = self.dependence.mtime(outname)
        for src in self.parser:
            obj = self.parser[src]
            mtime = self.dependence.mtime(obj)
            if mtime == 0 or mtime > outtime:
                update = True
                break
        if update:
            self.coremake.remove(self.parser.out)
            self.coremake.event(self.parser.events.get('prelink', []))
        retval = self.coremake.link(True, printmode)
        if retval:
            self.coremake.event(self.parser.events.get('postbuild', []))
            return 0
        return 3

    def build (self, printmode = 0):
        if not self.loaded:
            return 1
        retval = self.compile(printmode)
        if retval != 0:
            return 2
        retval = self.link(printmode)
        if retval != 0:
            return 3
        return 0

    def clean (self):
        if not self.loaded:
            return 1
        for src in self.parser:
            obj = self.parser[src]
            if obj != src:
                self.coremake.remove(obj)
        if self.loaded:
            self.coremake.remove(self.parser.out)
        return 0

    def rebuild (self, printmode = -1):
        if not self.loaded:
            return 1
        self.clean()
        return self.build(printmode)

    def execute (self):
        if not self.loaded:
            return 1
        outname = os.path.abspath(self.parser.out)
        if not self.parser.mode in ('exe'):
            sys.stderr.write('cannot execute: \'%s\'\n'%outname)
            sys.stderr.flush()
            return 8
        if not os.path.exists(outname):
            sys.stderr.write('cannot find: \'%s\'\n'%outname)
            sys.stderr.flush()
            return 9
        os.system('"%s"'%outname)
        return 0

    def info (self, name = ''):
        name = name.lower()
        if name == '': name = 'out'
        if name in ('out'):
            print (self.parser.out)
        return 0

def help():
    print ("iar easy make")
    return 0

#----------------------------------------------------------------------
# main program
#----------------------------------------------------------------------
def main(argv = None):
    # create main object
    make = iar_make()

    if argv == None:
        argv = sys.argv

    args = argv
    argv = argv[:1]
    options = {}

    for arg in args[1:]:
        if arg[:2] != '--':
            argv.append(arg)
            continue
        key = arg[2:].strip('\r\n\t ')
        val = None
        p1 = key.find('=')
        if p1 >= 0:
            val = key[p1 + 1:].strip('\r\n\t')
            key = key[:p1].strip('\r\n\t')
        options[key] = val

    inipath = ''
    if options.get('ini', None) is not None:
        inipath = options['ini']
        if '~' in inipath:
            inipath = os.path.expanduser(inipath)
        inipath = os.path.abspath(inipath)

    if len(argv) <= 1:
        version = '(iar_easy_make v1.0 %s)'%sys.platform
        print ('usage: "iar_easy_make.py [option] srcfile" %s'%version)
        print ('options  :  -b | -build      build project')
        print ('            -c | -compile    compile project')
        print ('            -r | -rebuild    rebuild project')
        print ('            -o | -out        show output file name')
        print ('            -h | -help       show help page')
        return 0

    if os.path.exists(inipath):
        global INIPATH
        INIPATH = inipath
    elif inipath:
        sys.stderr.write('error: not find %s\n'%inipath)
        sys.stderr.flush()
        return -1

    cmd, name = 'build', ''

    if len(argv) == 2:
        name = argv[1].strip(' ')
        if name in ('-h', '-help', '-help'):
            help()
            return 0

    if len(argv) >= 3:
        cmd = argv[1].strip(' ').lower()
        name = argv[2]
    else:
        if name[:1] == '-':
            print ('not enough parameter: %s'%name)
            return 0

    printmode = 3

    def int_safe(text, defval):
        num = defval
        try: num = int(text)
        except: pass
        return num

    def bool_safe(text, defval):
        if text is None:
            return True
        if text.lower() in ('true', '1', 'yes', 't'):
            return True
        if text.lower() in ('0', 'false', 'no', 'n'):
            return False
        return defval

    if 'cpu' in options:
        make.cpus = int_safe(options['cpu'], 1)

    ext = os.path.splitext(name)[-1].lower() 
    ft1 = ('.c', '.cpp', '.cxx')
    ft2 = ('.h', '.inc')
    ft3 = ('.mk')
    if not ((ext in ft1) or (ext in ft3)):
        sys.stderr.write('error: %s: unsupported file type\n'%(name))
        sys.stderr.flush()
        return -1

    retval = 0

    if cmd in ('b', '-b', 'build', '-build'):
        make.open(name)
        retval = make.build(printmode)
    elif cmd in ('c', '-c', 'compile', '-compile'):
        make.open(name)
        retval = make.compile(printmode)
    elif cmd in ('clean', '-clean'):
        make.open(name)
        retval = make.clean()
    elif cmd in ('r', '-r', 'rebuild', '-rebuild'):
        make.open(name)
        retval = make.rebuild(printmode)
    elif cmd in ('o', '-o', 'out', '-out'):
        make.open(name)
        make.info('outname');
    else:
        sys.stderr.write('unknow command: %s\n'%cmd)
        sys.stderr.flush()
        retval = 127
    return retval


if __name__ == '__main__':
    sys.exit( main() )

