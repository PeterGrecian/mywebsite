"""
Email forwarder: SES receives mail → S3 → this Lambda → SES sends to Gmail.

Rewrites From/Reply-To headers so Gmail can reply naturally.
"""

import email
import json
import os
import re

import boto3

FORWARD_TO = os.environ["FORWARD_TO"]
MAIL_BUCKET = os.environ["MAIL_BUCKET"]

s3 = boto3.client("s3")
ses = boto3.client("ses", region_name="eu-west-1")


def lambda_handler(event, context):
    record = event["Records"][0]
    ses_event = record["ses"]
    message_id = ses_event["mail"]["messageId"]

    # Fetch the raw email from S3
    obj = s3.get_object(Bucket=MAIL_BUCKET, Key=message_id)
    raw = obj["Body"].read()

    msg = email.message_from_bytes(raw)

    # Preserve original sender info
    original_from = msg.get("From", "unknown")
    original_to = ses_event["mail"]["destination"][0]

    # Rewrite headers for forwarding
    # From must be a verified SES identity (our domain)
    msg.replace_header("From", f"forwarded@petergrecian.co.uk")
    if msg.get("Reply-To") is None:
        msg["Reply-To"] = original_from

    # Replace To with forward destination
    msg.replace_header("To", FORWARD_TO)

    # Add forwarding info to subject
    subject = msg.get("Subject", "(no subject)")
    if not subject.startswith("[Fwd]"):
        msg.replace_header("Subject", f"[Fwd to {original_to}] {subject}")

    # Remove headers that interfere with SES sending
    for header in ["DKIM-Signature", "Return-Path", "Sender"]:
        if header in msg:
            del msg[header]

    ses.send_raw_email(
        Source="forwarded@petergrecian.co.uk",
        Destinations=[FORWARD_TO],
        RawMessage={"Data": msg.as_bytes()},
    )

    print(f"Forwarded {message_id}: {original_from} → {FORWARD_TO}")
    return {"status": "forwarded", "messageId": message_id}
