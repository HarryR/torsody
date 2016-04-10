__all__ = ('HomeView', )

from flask import Response, render_template, request
# current_app, url_for, redirect
from flask.views import MethodView
from flask_wtf import Form
from wtforms import TextField, validators
from .backend import Api
import random, string

class View(MethodView):
    _template = None

    def setup(self):
        pass

    def dispatch_request(self, *args, **kwargs):
        self.setup()
        try:
            response = super(View, self).dispatch_request(*args, **kwargs)
        except Response as response:
            return response
        if isinstance(response, dict) and self._template is not None:
            # Template gets all public properties of the class
            # Along with the dictionary the method returned...
            template_vars = {key: value for key, value in self.__dict__.iteritems() if key[0] != '_'}
            template_vars.update(**response)
            return render_template(self._template, **template_vars)
        else:
            return response

    def __init__(self, *args, **kwargs):
        super(View, self).__init__(*args, **kwargs)


class CreateForm(Form):
    username = TextField('username', validators=[validators.DataRequired(),
                                                 validators.Regexp(r'^[a-zA-Z0-9]{2,16}$')])

class HomeView(View):
    _template = 'home.html'
    def __init__(self):
        self.createform = None
        self.newaccount = None

    def setup(self):
        self.createform = CreateForm()
        self.newaccount = None

    def post(self):
        action = request.form.get('action')
        if action == "delete":
            hostname = request.form.get('hostname')
            Api.call('delete', hostname)
        elif action == "create":
            form = self.createform
            if form.validate():
                username = form.username.data
                self.newaccount = Api.call('create', username)
        return self.get()

    def get(self):
        password = ''.join(random.choice(string.lowercase + string.digits) for _ in range(16))
        self.createform.username.data = password
        return {
            'hostnames': Api.call('list')
        }