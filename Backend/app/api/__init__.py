def init_app(app):
    from .signin import api as signin_bs
    app.register_blueprint(signin_bs)

    from .meetspace import api as meetspace_bs
    app.register_blueprint(meetspace_bs)
