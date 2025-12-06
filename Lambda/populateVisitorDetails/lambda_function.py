import boto3
import json
import base64

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('VisitorRequestDetails')

def lambda_handler(event, context):
    try:
        response = table.scan()
        users = response['Items']

        # Process the users, encoding Binary types as base64
        result = [
            {
                "id": user["faceId"],
                "name": user["name"],
                "mail": user["email"],
                "status": user["status"],
                "image": base64.b64encode(user["image"].value).decode('utf-8') if "image" in user else None
            }
            for user in users
        ]

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(result)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"error": str(e)})
        }
