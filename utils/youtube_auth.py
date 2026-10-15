import os

import httplib2
from googleapiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the Google API Console at
# https://console.cloud.google.com/.
# Please ensure that you have enabled the YouTube Data API and the YouTube
# Analytics API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = "credentials/client_secrets.json"

TOKENS_FILE = "credentials/tokens.json"

# Upload videos to the authenticated user's channel.
UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"

# Read the channel's uploads, to find videos that were uploaded by hand.
READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"

# Read the channel's YouTube Analytics reports.
ANALYTICS_SCOPE = "https://www.googleapis.com/auth/yt-analytics.readonly"

ALL_SCOPES = [UPLOAD_SCOPE, READONLY_SCOPE, ANALYTICS_SCOPE]

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.cloud.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(__file__)), CLIENT_SECRETS_FILE)
)


class CredentialsError(Exception):
    pass


def authorize(args):
    """Run the browser OAuth flow for every scope the app uses and save the tokens."""
    flow = flow_from_clientsecrets(
        CLIENT_SECRETS_FILE,
        scope=ALL_SCOPES,
        message=MISSING_CLIENT_SECRETS_MESSAGE,
    )

    return run_flow(flow, Storage(TOKENS_FILE), args)


def has_saved_credentials() -> bool:
    return os.path.exists(TOKENS_FILE)


def load_credentials(scopes=()):
    """Load the saved tokens without prompting, so unattended runs fail instead of hanging."""
    credentials = Storage(TOKENS_FILE).get()

    if credentials is None or credentials.invalid:
        raise CredentialsError(
            f"No valid YouTube credentials in {TOKENS_FILE}, "
            "run `python update_tokens.py` to log in again"
        )

    if scopes and not credentials.has_scopes(scopes):
        missing = ", ".join(sorted(set(scopes) - set(credentials.scopes)))
        raise CredentialsError(
            f"The saved YouTube credentials are missing access to {missing}, "
            "run `python update_tokens.py` to grant it"
        )

    return credentials


def build_service(name: str, version: str, credentials):
    return build(name, version, http=credentials.authorize(httplib2.Http()))
