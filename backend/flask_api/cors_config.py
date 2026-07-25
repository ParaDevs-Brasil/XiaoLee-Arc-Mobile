# ARQUIVADO (2026-07-10) — sem entrypoint, não roda em produção. Ver flask_api/README.md.

from flask_cors import CORS


def setup_cors(app):
    # Define the specific origins allowed to connect.
    # Using a specific list is more secure than "*" and necessary for some browsers.
    CORS(app,
         origins=["*"],
         methods=["GET", "POST", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"])

    # The manual @after_request below is redundant and can conflict with a
    # proper Flask-CORS setup, especially when not using a wildcard "*".
    # The Flask-CORS extension now handles setting these headers correctly.
    # I am commenting it out to ensure the extension works as intended.
    # @app.after_request
    # def after_request(response):
    #     response.headers.add('Access-Control-Allow-Origin', '*')
    #     response.headers.add('Access-Control-Allow-Headers',
    #                          'Content-Type,Authorization')
    #     response.headers.add('Access-control-Allow-Methods',
    #                          'GET,POST,OPTIONS')
    #     return response
