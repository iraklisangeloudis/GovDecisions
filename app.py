from flask import Flask
from routes.decisions import decisions_bp

app = Flask(__name__)

app.register_blueprint(decisions_bp)

if __name__ == '__main__':
    app.run(debug=True)
