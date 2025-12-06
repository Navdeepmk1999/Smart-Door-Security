import json
import os
import boto3
from boto3.dynamodb.conditions import Key


def lambda_handler(event, context):
    email = event.get('email', '').strip().lower()
    password = event.get('password', '')
    
    # Basic input validation
    if not email or not password:
        return {
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
        },
            "statusCode": 400,
            "body": json.dumps({"error": "error and password are required."})
        }

    # Initialize the DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    owners_table = dynamodb.Table('Owners')

    # Query the table for the given email
    try:
        response = owners_table.query(
            KeyConditionExpression=Key('email').eq(email)
        )
    except Exception as e:
        # Handle potential DynamoDB errors
        return {
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
        },
            "statusCode": 500,
            "body": json.dumps({"error": "Error accessing the database.", "details": str(e)})
        }

    # Check if we got any matching items
    if 'Items' not in response or len(response['Items']) == 0:
        return {
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
        },
            "statusCode": 404,
            "body": json.dumps({"error": "Email not found."})
        }

    # We expect a single item since it's keyed by email
    owner_item = response['Items'][0]
    stored_password = owner_item.get('password')

    # Validate the password
    # For this example, we're assuming plain text validation.
    # In real implementations, you'd use hashing and compare accordingly.
    if password == stored_password:
        # Credentials match
        return {
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
        },
            "statusCode": 200,
            "body": json.dumps({"message": "Validation successful."})
        }
    else:
        # Wrong password
        return {
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
        },
            "statusCode": 401,
            "body": json.dumps({"error": "Invalid password."})
        }

