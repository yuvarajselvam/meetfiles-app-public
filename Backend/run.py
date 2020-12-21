import os

from app import create_app

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app = create_app()
    app.run()
