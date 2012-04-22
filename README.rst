#################
djangosenchatools
#################

Django management commands for the JSBuilder commands in `Sencha SDK Tools`_.
Unfortunately, the JSBuilder commands provided by Sencha Tools needs some
workarounds to work when the HTML document and resources are not in the same
directory. We have turned these workarounds into a Django management command
available in the *djangosenchatools* app.


Issues/contribute
=================

Report any issues at the `github project page <djangosenchatools>`_, and feel free
to add your own guides/experiences to the wiki, and to contribute changes using
pull requests.


Install
=======

Install the python package::

    pip install djangosenchatools


Add it to your django project::

    INSTALLED_APPS = [
        ...
        'djangosenchatools'
    ]


Usage
=====

First, we need a Django ExtJS4 application. See `django_extjs4_examples`_ for
an example application. We use the ``minimal_extjs4_app`` as our example.

.. note:: The ``senchatoolsbuild`` management command runs ``collectstatic``.

.. note:: You need to run the Django server (``manage.py runserver``) for all commands except --listall.


Build one app
-------------

1. Start the Django server (``python manage.py runserver``).
2. Run::

    python manage.py senchatoolsbuild --url http://localhost:8000/minimal_extjs4_app/ --outdir /path/to/outdir

With ``--url`` and ``--outdir``, the senchatoolsbuild command runs ``sencha
create jsb`` and ``sencha build``, and puts the result in the ``--outdir``.
Run with ``-v3`` for full debug output if you want to see what the command does.


Build all INSTALLED_APPS
------------------------

``senchatoolsbuild`` can autodetect sencha apps and build them all in their
respective static directories. Run with ``--help`` and see the help for
``--buildall`` to see how apps are detected.

To list detected apps, their ``--outdir`` and ``--url``, run::

    python manage.py senchatoolsbuild --listall

Add ``-v3`` to see skipped apps, and why they are skipped.

To build all detected apps, run::

    python manage.py senchatoolsbuild --buildall


Build one app by name
---------------------

You can build a single app in ``INSTALLED_APPS`` using the same method of
detecting outdir and url as ``--buildall`` using ``--app``::

    python manage.py senchatoolsbuild --app minimal_extjs4_app


Integration with django_extjs4
==============================

This app is made to work with `django_extjs4`_, however they are losely
coupled. The only place where you are likely to notice that they work together
is that ``senchatoolsbuild`` checks that ``settings.EXTJS4_DEBUG==True``. You
can disable this check using ``--no-check-settings``.


Building apps that require authentication
=========================================

Add the following to your ``settings.py``::

    MIDDLEWARE_CLASSES += ['djangosenchatools.auth.SettingUserMiddleware']
    AUTHENTICATION_BACKENDS = ('djangosenchatools.auth.SettingUserBackend',)
    SENCHATOOLS_USER = 'myuser'

Where ``SENCHATOOLS_USER`` is the user that you want to be authenticated as
(the user must exist). **NEVER** use this backend/middleware in production.


Reccommended setup
------------------

We reccommend that you create a separate settings.py for ``senchatoolsbuild``
where you set the required settings. Here is our ``djangosenchatools_settings.py``::

    from settings import *
    EXTJS4_DEBUG = True
    MIDDLEWARE_CLASSES += ['djangosenchatools.auth.SettingUserMiddleware']
    AUTHENTICATION_BACKENDS = ('djangosenchatools.auth.SettingUserBackend',)
    SENCHATOOLS_USER = 'grandma'

We use this settings module with ``runserver`` whenever we build apps using
``senchatoolsbuild``::

    $ python manage.py runserver --settings djangosenchatools_settings
    and in another terminal:
    $ python manage.py senchatoolsbuild --buildall


.. _`Sencha SDK Tools`: http://www.sencha.com/products/sdk-tools
.. _`django_extjs4`: https://github.com/espenak/django_extjs4
.. _`django_extjs4_examples`: https://github.com/espenak/django_extjs4_examples
.. _`djangosenchatools`: https://github.com/espenak/djangosenchatools

