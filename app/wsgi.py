if __package__ in (None, ""):
    # When used as a top-level module (Docker: wsgi:application)
    from app import app as application  # type: ignore
else:
    # When imported as package module (VM: app.wsgi:application)
    from .app import app as application  # type: ignore
