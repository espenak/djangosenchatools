from fnmatch import fnmatch
import logging
from django.conf import settings
from watchdog.events import FileSystemEventHandler

log = logging.getLogger('senchatoolsbuild')



class DjangoFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.excludepatterns = getattr(settings, 'DJANGOSENCHATOOLS_WATCH_EXCLUDE',
                                      ['*.*.swp', '*~', '*.pyc', '*.pyo',
                                       '*app-all.js', '*all-classes.js'])
        self.includepatterns = getattr(settings, 'DJANGOSENCHATOOLS_WATCH_INCLUDE',
                                       ['*.js'])
        self.callback = callback
        super(DjangoFileSystemEventHandler, self).__init__()

    def on_any_event(self, event):
        callback = self.callback
        path = event.src_path
        event_type = event.event_type
        if event.is_directory:
            log.debug('Ignored {event_type}-event on {path} because it is a directory'.format(**vars()))
            return
        if self.includepatterns:
            match = False
            for patt in self.includepatterns:
                if fnmatch(path, patt):
                    match = True
                    break
            if not match:
                includepatterns_str = repr(self.includepatterns)
                log.debug('Ignored {event_type}-event on {path} because it does not match any of: {includepatterns_str}'.format(**vars()))
                return
        for ignorepatt in self.excludepatterns:
            if fnmatch(path, ignorepatt):
                log.debug('Ignored {event_type}-event on {path} because of the "{ignorepatt}" excludepattern'.format(**vars()))
                return
        log.info('Change of type={0} detected in: {1}'.format(event.event_type, path))
        callback()
