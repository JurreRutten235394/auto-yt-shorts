#!/usr/bin/python

from oauth2client.tools import argparser

from utils.notifications import send_error_notification, send_success_notification
from utils.youtube_auth import TOKENS_FILE, authorize


def update_credentials():
    """Update YouTube API credentials by forcing re-authentication."""
    try:
        print("Updating YouTube API credentials...")

        # Get new credentials
        args = argparser.parse_args([])
        credentials = authorize(args)

        if credentials:
            success_msg = f"Successfully updated credentials and saved to {TOKENS_FILE}"
            print(success_msg)
            send_success_notification(success_msg, "Credential Update")
        else:
            error_msg = "Failed to update credentials"
            print(error_msg)
            send_error_notification(error_msg, context="Credential Update")

    except Exception as e:
        error_msg = "Failed to update YouTube API credentials"
        print(f"{error_msg}: {e}")
        send_error_notification(error_msg, e, "Credential Update")


if __name__ == "__main__":
    update_credentials()
