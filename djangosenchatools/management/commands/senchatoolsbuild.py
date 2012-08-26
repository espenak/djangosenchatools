from urlparse import urlparse
import logging
from os.path import join, dirname, isdir, relpath, abspath, sep, exists
from os import remove
from subprocess import call
from tempfile import mkdtemp
from shutil import rmtree
import json
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.core import management
from django.conf import settings
from django.utils.importlib import import_module
from djangosenchatools.buildserver import build_with_buildserver

log = logging.getLogger('senchatoolsbuild')


def get_appinfo(app):
    mod = import_module(app)
    moddir = dirname(mod.__file__)
    if exists(mod.__file__) and isdir(moddir):
        appname = mod.__name__.split('.')[-1]
        outdir = join(moddir, 'static', appname)
        appdir = join(outdir, 'app')
        if isdir(appdir):
            log.debug('Found ExtJS app: %s', appname)
            return (outdir, appname)
        else:
            log.debug('%s is not an ExtJS app (%s does not exist).', appname, appdir)
    raise LookupError()

def get_installed_extjs_apps():
    """
    Get all installed extjs apps.

    :return: List of ``(appdir, module, appname)``.
    """
    installed_apps = []
    checked = set()
    for app in settings.INSTALLED_APPS:
        if not app.startswith('django.') and not app in checked:
            checked.add(app)
            try:
                installed_apps.append(get_appinfo(app))
            except LookupError, e:
                pass
    return installed_apps

def setup_logging(verbosity):
    if verbosity < 1:
        loglevel = logging.ERROR
    elif verbosity < 2:
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
        self.configpath = join(outdir, 'app.jsb3')
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

    def createAndWriteCleanJsbConfig(self):
        jsb = self.createCleanJsbConfig()
        open(self.configpath, 'wb').write(jsb)
        return jsb

    def readJsbConfig(self):
        return open(self.configpath, 'rb').read()

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
        #del appall['files'][1]
        for file in appall['files']:
            file['path'] = self.unixstyle_outdir

        # Make sure the output files are correct (and that sencha/jsbuilder have not changed their format).
        assert(appall['files'][0]['name'] == 'all-classes.js')
        assert(appall['files'][1]['name'] == 'app.js')
        assert(len(appall['files']) == 2)
        assert(appall['target'] == 'app-all.js')

    def buildFromJsbString(self, jsb, nocompressjs=False):
        """
        Build from the given config file using ``sencha build``.

        :param jsb: The JSB config as a string.
        :param nocompressjs: Compress the javascript? If ``True``, run ``sencha build --nocompress``.
        """
        tempconffile = 'temp-app.jsb3'
        cmd = ['sencha', 'build', '-p', tempconffile, '-d', self.outdir]
        if nocompressjs:
            cmd.append('--nocompress')
        open(tempconffile, 'w').write(jsb)
        log.info('Running: %s', ' '.join(cmd))
        try:
            call(cmd)
        finally:
            remove(tempconffile)

    def configureAndBuild(self, nocompressjs=False):
        """
        Run :meth:`createCleanJsbConfig` and :meth:`build`.
        """
        jsb = self.createCleanJsbConfig()
        self.buildFromJsbString(jsb, nocompressjs)


class Command(BaseCommand):
    help = 'Build sencha javascript apps.'
    option_list = BaseCommand.option_list + (
        make_option('--no-collectstatic',
            action='store_false',
            dest='collectstatic',
            default=True,
            help='Do not run collectstatic before building.'),
        make_option('--dont-use-buildserver',
            action='store_false',
            dest='use_buildserver',
            default=True,
            help='We normally start a Django server in a thread while building the app(s). If you prefer to manually start your own server, use this option.'),
        make_option('--url',
            dest='url',
            help="The URL path to your application's HTML entry point. Same as the --app-entry parameter for 'sencha create jsb', except that we only support urls."),
        make_option('--outdir',
            dest='outdir',
            help="Filesystem path to the output directory."),
        make_option('--watch',
            dest='watchdir',
            help="Filesystem path a directory that should be watched for changes. Changes trigger a re-run of this command with the same options."),
        make_option('--app',
            dest='app',
            help=("App to build. An alternative to using --url and --outdir. "
                  "Looks up information about a single just like --buildall does "
                  "for all apps.")),
        make_option('--buildall',
            action='store_true',
            default=False,
            dest='buildall',
            help=('Automatically find and build apps. Any django app with a '
                  '``<appdir>/static/<appname>/app`` directory is considered an ExtJS '
                  'app, and expected to be available at '
                  '``http://localhost:15041/<appname>/``. The outdir for each app is '
                  '``<appdir>/static/<appname>/``. Note: You can override the url with --urlpattern.')),
        make_option('--listall',
            action='store_true',
            default=False,
            dest='listall',
            help='List information about the apps that will be built by --buildall.'),
        make_option('--no-check-settings',
            action='store_false',
            default=True,
            dest='check_settings',
            help='Do not abort if settings.EXTJS4_DEBUG is False. EXTJS4_DEBUG is a setting introduced by the django_extjs4 app.'),
        make_option('--urlpattern',
            dest='urlpattern',
            default='http://localhost:15041/{appname}/',
            help="URL pattern used to create urls for apps when using --buildall or --app. Defaults to 'http://localhost:15041/{appname}/'."),
        make_option('--nocompress',
            action='store_true',
            dest='nocompressjs',
            default=False,
            help='Forwarded to "sencha build". See "sencha help build".'),
        make_option('--no-jsbcreate',
            action='store_false',
            dest='create_jsb',
            default=True,
            help='Do not run "sencha create" to create/update the JSB-file.')
        )

    def handle(self, *args, **options):
        setup_logging(get_verbosity(options))
        self.nocompressjs = options['nocompressjs']
        self.urlpattern = options['urlpattern']
        self.use_buildserver = options['use_buildserver']
        self.check_settings = options['check_settings']
        self.collectstatic = options['collectstatic']
        self.app = options['app']
        self.url = options['url']
        self.outdir = options['outdir']
        self.buildall = options['buildall']
        self.watchdir = options['watchdir']
        self.create_jsb = options['create_jsb']
        build_single = (self.url and self.outdir)

        if build_single:
            self.hostname, self.port = self._parse_url(self.url)
        else:
            self.hostname, self.port = self._parse_url(self.urlpattern)

        if options['listall']:
            self._listAllApps()
            return
        if build_single or self.buildall or self.app:
            if self.watchdir:
                self._watch()
            else:
                self._run()
        else:
            raise CommandError('One of --listall, --buildall or --url and --outdir is required.')


    def _run(self):
        if self.check_settings:
            if not getattr(settings, 'EXTJS4_DEBUG', False):
                raise CommandError('settings.EXTJS4_DEBUG==False. Use --no-check-settings to ignore this check.')
        else:
            log.info('Skipping check for settings.EXTJS4_DEBUG.')

        if self.collectstatic:
            log.info('Running "collectstatic"')
            management.call_command('collectstatic', verbosity=1, interactive=False)
        else:
            log.info('Skipping "collectstatic"')

        if self.buildall:
            self._buildAllApps()
        elif self.app:
            self._buildAppByName(self.app)
        else:
            outdir = abspath(self.outdir)
            self._buildApp(outdir, self.url)
            log.info('Successfully built {url}. Results are in: {outdir}'.format(url=self.url,
                                                                                 outdir=outdir))

    def _getUrl(self, appname):
        return self.urlpattern.format(appname=appname)

    def _parse_url(self, url):
        o = urlparse(url)
        return o.hostname, o.port

    def _iterAllApps(self):
        for outdir, appname in get_installed_extjs_apps():
            url = self._getUrl(appname)
            yield outdir, appname, url

    def _buildAppByName(self, app):
        try:
            outdir, appname = get_appinfo(app)
        except LookupError:
            raise CommandError('Could not find "{0}".'.format(app))
        else:
            url = self._getUrl(appname)
            log.info('Building {appname} ({url}).'.format(**vars()))
            self._buildApp(outdir, url)
            log.info('Successfully built {appname} ({url}). Results are in: {outdir}'.format(**vars()))

    def _buildAllApps(self):
        for outdir, appname, url in self._iterAllApps():
            log.info('Building {appname} ({url}).'.format(**vars()))
            self._buildApp(outdir, url)
            log.info('Successfully built {appname} ({url}). Results are in: {outdir}'.format(**vars()))

    def _listAllApps(self):
        for outdir, appname, url in self._iterAllApps():
            print
            print '{appname}:'.format(appname=appname)
            print '    outdir:', outdir
            print '    url:', url

    def _buildApp(self, outdir, url):
        sencha = SenchaToolsWrapper(outdir, url)
        if self.create_jsb:
            def builder():
                jsb = sencha.createAndWriteCleanJsbConfig()
            if self.use_buildserver:
                build_with_buildserver(self.hostname, self.port, builder)
            else:
                builder()
        jsb = sencha.readJsbConfig()
        log.info('Building app-all.js from %s (copied to temp-app.jsb3)', sencha.configpath)
        sencha.buildFromJsbString(jsb=jsb,
                                  nocompressjs=self.nocompressjs)

    def _watch(self):
        from djangosenchatools.watch import DjangoFileSystemEventHandler
        from watchdog.observers import Observer
        import time

        log.info('Listening for file events in: %s', self.watchdir)
        event_handler = DjangoFileSystemEventHandler(self._run)
        observer = Observer()
        observer.schedule(event_handler, self.watchdir, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(0.3)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
