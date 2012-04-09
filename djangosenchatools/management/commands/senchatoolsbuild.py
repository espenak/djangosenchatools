import logging
from os.path import join, dirname, isdir, relpath, abspath, sep
from os import getcwd, remove
from subprocess import call
from tempfile import mkdtemp
from shutil import rmtree
import json
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.core import management
from django.conf import settings

log = logging.getLogger('senchatoolsbuild')



#def get_js_apps():
    #apps = []
    #for moddir, mod, appname in get_installed_apps():
        #outdir = join(moddir, 'static', appname)
        #appdir = join(outdir, 'app')
        #if isdir(appdir):
            #apps.append((outdir, appname))
    #return apps

def setup_logging(verbosity):
    if verbosity < 1:
        loglevel = logging.ERROR
    elif verbosity == 1:
        loglevel = logging.WARNING
    elif verbosity == 2:
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)

def get_verbosity(options):
    return int(options.get('verbosity', '1'))


class SenchaToolsWrapper(object):
    def __init__(self, outdir, url):
        """
        :param outdir: The directory where the result is placed.
        :param url: The url forwarded as the ``--app-entry`` argument to ``sencha create jsb``.
        """
        self.url = url
        self.outdir = outdir
        self.unixstyle_outdir = relpath(outdir).replace(sep, '/') + '/' # Make sure we have a unix-style path with trailing /
        self.static_root = relpath(settings.STATIC_ROOT)

    def createJsbConfig(self):
        """
        Create JSB config file using ``sencha create jsb``.

        :return: The created jsb3 config as a string.
        """
        tempdir = mkdtemp()
        tempfile = join(tempdir, 'app.jsb3')
        cmd = ['sencha', 'create', 'jsb', '-a', self.url, '-p', tempfile]
        log.debug('Running: %s', ' '.join(cmd))
        call(cmd)
        jsb3 = open(tempfile).read()
        rmtree(tempdir)
        return jsb3

    def cleanJsbConfig(self, jsbconfig):
        """
        Clean up the JSB config.
        """
        config = json.loads(jsbconfig)
        self._cleanJsbAllClassesSection(config)
        self._cleanJsbAppAllSection(config)
        return json.dumps(config, indent=4)

    def createCleanJsbConfig(self):
        """
        Run :meth:`createJsbConfig`, clean up the JSB with
        :meth:`cleanJsbConfig` and return the result.
        """
        jsb = self.createJsbConfig()
        log.debug('sencha generated JSB config: %s', jsb)
        jsb = self.cleanJsbConfig(jsb)
        log.debug('cleaned JSB config: %s', jsb)
        return jsb

    def _cleanJsbAllClassesSection(self, config):
        """
        Fixes two issues with the sencha created JSB:

            - All extjs urls are prefixed by ``../static`` instead of
              ``/static`` (no idea why).
            - We assume static files are served at ``/static``, but collectstatic may
              not build files in ``static/``. Therefore, we replace ``/static`` with
              the relative path to ``settings.STATIC_ROOT``.
        """
        allclasses = config['builds'][0]
        for fileinfo in allclasses['files']:
            path = fileinfo['path']
            if path.startswith('..'):
                path = path[2:]
            path = path.replace('/static', self.static_root)
            fileinfo['path'] = path

    def _cleanJsbAppAllSection(self, config):
        appall = config['builds'][1]
        del appall['files'][1]
        assert(len(appall['files']) == 1)
        appall['files'][0]['path'] = self.unixstyle_outdir

    def build(self, cleanedJsbConfig, nocompressjs=False):
        """
        Build JSB from the given config file (a string) using ``sencha build``.

        :param nocompressjs: Compress the javascript? If ``True``, run ``sencha build --nocompress``.
        """
        tempconffile = 'temp-app.jsb3'
        open(tempconffile, 'w').write(cleanedJsbConfig)
        cmd = ['sencha', 'build', '-p', tempconffile, '-d', self.outdir]
        if nocompressjs:
            cmd.append('--nocompress')
        log.debug('Running: %s', ' '.join(cmd))
        call(cmd)
        remove(tempconffile)

    def configureAndBuild(self, nocompressjs=False):
        """
        Run :meth:`createCleanJsbConfig` and :meth:`build`.
        """
        jsb = self.createCleanJsbConfig()
        self.build(jsb, nocompressjs)


class Command(BaseCommand):
    help = 'Build sencha javascript apps.'
    option_list = BaseCommand.option_list + (
        make_option('--no-collectstatic',
            action='store_false',
            dest='collectstatic',
            default=True,
            help='Do not run collectstatic before building.'),
        make_option('--url',
            dest='url',
            help="The URL path to your application's HTML entry point. Same as the --app-entry parameter for 'sencha create jsb', except that we only support urls."),
        make_option('--outdir',
            dest='outdir',
            help="Filesystem path to the output directory."),
        make_option('--nocompress',
            action='store_true',
            dest='nocompressjs',
            default=False,
            help='Forwarded to "sencha build". See "sencha help build".'),
        )


    def handle(self, *args, **options):
        self.nocompressjs = options['nocompressjs']

        setup_logging(get_verbosity(options))
        if options['collectstatic']:
            log.info('Running "collectstatic"')
            management.call_command('collectstatic', verbosity=1, interactive=False)
        else:
            log.info('Skipping "collectstatic"')

        #for appinfo in get_js_apps():
            #self._buildApp(*appinfo)
        url = options['url']
        outdir = abspath(options['outdir'])
        self._buildApp(outdir, url)

    def _buildApp(self, outdir, url):
        SenchaToolsWrapper(outdir, url).configureAndBuild(self.nocompressjs)
