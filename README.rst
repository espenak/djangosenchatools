#################
djangosenchatools
#################

Django_ management commands for the JSBuilder commands in `Sencha SDK Tools`_.
Unfortunately, the JSBuilder commands provided by Sencha Tools needs some
workarounds to work when the HTML document and resources are not in the same
directory. We have turned these workarounds into a Django management command
available in the *djangosenchatools* app.

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

**warning:** The ``senchatoolsbuild`` management command runs ``collectstatic``.


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


.. _Django: http://www.sencha.com/products/sdk-tools
.. _`Sencha SDK Tools`: http://www.sencha.com/products/sdk-tools
.. _`django_extjs4`: https://github.com/espenak/django_extjs4
.. _`django_extjs4_examples`: https://github.com/espenak/django_extjs4_examples