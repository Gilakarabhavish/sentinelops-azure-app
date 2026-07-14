from flask import Flask, jsonify, render_template

application = Flask(__name__)


@application.route("/")
def home():
    return render_template("index.html")


@application.route("/health")
def health():
    return jsonify(
        status="healthy",
        application="SentinelOps Lite",
        environment="Azure App Service Linux"
    ), 200


if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000)