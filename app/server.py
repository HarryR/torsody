__all__ = ('run_server',)


import logging
from os import path
import gevent
from gevent.pywsgi import WSGIServer
from flask import Flask, Blueprint
from flask.ext.assets import Environment
from .frontend import HomeView
from .backend import Api

LOGGER = logging.getLogger()


##############################################################################


class FrontendBlueprint(Blueprint):
    def __init__(self, name='frontend'):
        cwd = path.dirname(path.realpath(__file__))
        template_folder = path.join(cwd, 'templates')
        static_folder = path.join(cwd, 'static')
        super(FrontendBlueprint, self).__init__(name, __name__,
                                                template_folder=template_folder,
                                                static_folder=static_folder,
                                                static_url_path='/static')
        self._setup_urls()

    def _setup_urls(self):
        self.add_url_rule('/', view_func=HomeView.as_view('home'))



##############################################################################



def run_server(options):
    api_listener = Api()
    gevent.spawn(api_listener.run)
    #
    # Setup flask app
    static_url_path = "/changed-so-it-doesnt-conflict-with-blueprint-static-path"
    app = Flask(__name__, static_url_path=static_url_path)
    app.config.from_pyfile(options["config"].name)
    app.register_blueprint(FrontendBlueprint())
    #
    # JS/CSS & HTML minification in production
    if not app.config.get('DEBUG'):
        from .misc.jinja2htmlcompress import HTMLCompress
        app.jinja_env.add_extension(HTMLCompress)
    assets = Environment()
    assets.init_app(app)
    #
    # Run server
    http = WSGIServer((options['http_host'], options['http_port']), app)
    LOGGER.info('Listening on %s:%s', options['http_host'], options['http_port'])
    try:
        http.serve_forever()
        return 0
    except KeyboardInterrupt:
        http.stop()
        api_listener.stop()
        LOGGER.info('Application Terminated')
        return 0