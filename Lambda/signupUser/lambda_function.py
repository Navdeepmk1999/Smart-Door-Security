import json
import boto3
import os
import re
from datetime import datetime

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table("Owners")

def validate_email(email):
    """Simple regex for email validation."""
    regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.match(regex, email)

def lambda_handler(event, context):
    try:
        # Parse the request body
        name = event.get('name', '').strip()
        email = event.get('email', '').strip().lower()
        password = event.get('password', '')

        # Input validation
        if not name or not email or not password:
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'Name, email, and password are required.'})
            }

        if not validate_email(email):
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'Invalid email format.'})
            }

        # Check if user already exists
        response = table.get_item(Key={'email': email})
        if 'Item' in response:
            return {
                'statusCode': 409,
                'body': json.dumps({'message': 'User already exists.'})
            }

        # Store the user in DynamoDB
        user_item = {
            'email': email,
            'name': name,
            'password':password,
            'createdAt': datetime.utcnow().isoformat() + 'Z'
        }

        table.put_item(Item=user_item)

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'User created successfully.'})
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Internal server error.'})
        }
