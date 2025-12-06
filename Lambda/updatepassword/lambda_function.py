import json
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Owners')

def lambda_handler(event, context):
    try:
        # Parse input from the request body
        body = json.loads(event['body'])
        user_id = body.get('userId')
        old_password = body.get('oldPassword')
        new_password = body.get('newPassword')

        # Validate inputs
        if not user_id or not old_password or not new_password:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid input. All fields are required."})
            }

        # Fetch user from DynamoDB
        response = table.get_item(Key={'email': user_id})
        user = response.get('Item')

        if not user or user['password'] != old_password:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Old password is incorrect."})
            }

        # Update password
        table.update_item(
            Key={'email': user_id},
            UpdateExpression="SET password = :new_password",
            ExpressionAttributeValues={':new_password': new_password}
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Password updated successfully."})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
