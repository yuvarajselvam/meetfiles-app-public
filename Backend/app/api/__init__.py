def init_app(app):
    from .signin import api as signin_bp
    app.register_blueprint(signin_bp)

    from .user import api as user_bp
    app.register_blueprint(user_bp)

    from .meetspace import api as meetspace_bp
    app.register_blueprint(meetspace_bp)

    from .meetsection import api as meetsection_bp
    app.register_blueprint(meetsection_bp)

    from .event import api as event_bp
    app.register_blueprint(event_bp)
