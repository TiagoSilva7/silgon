try:
    import flask
    print('flask-ok', flask.__version__)
except Exception as e:
    print('flask-error', type(e).__name__, str(e))
