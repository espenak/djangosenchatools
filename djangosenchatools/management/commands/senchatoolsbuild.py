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
        #del appall['files'][1]
        for file in appall['files']:
            file['path'] = self.unixstyle_outdir

        # Make sure the output files are correct (and that sencha/jsbuilder have not changed their format).
        assert(appall['files'][0]['name'] == 'all-classes.js')
        assert(appall['files'][1]['name'] == 'app.js')
        assert(len(appall['files']) == 2)
        assert(appall['target'] == 'app-all.js')

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
                  '``http://localhost:8000/<appname>/``. The outdir for each app is '
                  '``<appdir>/static/<appname>/``')),
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
            default='http://localhost:8000/{appname}/',
            help="URL pattern used to create urls for apps when using --buildall. Defaults to 'http://localhost:8000/{appname}/'."),
        make_option('--nocompress',
            action='store_true',
            dest='nocompressjs',
            default=False,
            help='Forwarded to "sencha build". See "sencha help build".'),
        )

    def handle(self, *args, **options):
        self.nocompressjs = options['nocompressjs']
        self.urlpattern = options['urlpattern']
        url = options['url']
        outdir = options['outdir']
        buildall = options['buildall']
        listall = options['listall']
        app = options['app']
        check_settings = options['check_settings']
        setup_logging(get_verbosity(options))
        build_single = (url and outdir)

        if listall:
            self._listAllApps()
            return
        if build_single or buildall or app:
            if check_settings:
                if not getattr(settings, 'EXTJS4_DEBUG', False):
                    raise CommandError('settings.EXTJS4_DEBUG==False. Use --no-check-settings to ignore this check.')
            else:
                log.info('Skipping check for settings.EXTJS4_DEBUG.')

            if options['collectstatic']:
                log.info('Running "collectstatic"')
                management.call_command('collectstatic', verbosity=1, interactive=False)
            else:
                log.info('Skipping "collectstatic"')

            if buildall:
                self._buildAllApps()
            elif app:
                self._buildAppByName(app)
            else:
                outdir = abspath(outdir)
                self._buildApp(outdir, url)
                log.info('Successfully built {url}. Results are in: {outdir}'.format(**vars()))
        else:
            raise CommandError('One of --listall, --buildall or --url and --outdir is required.')


    def _getUrl(self, appname):
        return self.urlpattern.format(appname=appname)

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
        SenchaToolsWrapper(outdir, url).configureAndBuild(self.nocompressjs)
