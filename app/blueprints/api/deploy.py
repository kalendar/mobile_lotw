from flask import Flask, request
from .base import bp
from os import getenv

@bp.get("/api/v1/deploy")

def deploy():
    # Get the API_KEY parameter from the request's query parameters
    api_key = request.args.get('API_KEY')

    # Check if the API_KEY is correct (replace 'your_secret_key' with your actual secret key)
    if api_key == getenv('API_KEY'):
        # Execute the shell script
        import subprocess
        subprocess.run([getenv('DEPLOY_SCRIPT_PATH')], shell=True)
        return 'Deployed successfully.'

    # If the API_KEY is incorrect, return an error message
    return 'Unauthorized.', 401