import logging
import subprocess


def secret_leak(settings):
    secret = settings.api_key
    # ruleid: runa-secret-to-observable-output
    logging.error("credential=%s", secret)


def response_execution(response):
    command = response.json()
    # ruleid: runa-http-response-to-code-execution
    subprocess.run(command)
