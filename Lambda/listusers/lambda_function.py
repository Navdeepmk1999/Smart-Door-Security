import boto3
import json
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
log_table = dynamodb.Table('SmartDoorLogs')

# Initialize AWS client
s3 = boto3.client('s3')

# Define S3 bucket (ensure this matches where user photos are stored)
S3_BUCKET = "my-user-photos-bucket"

def lambda_handler(event, context):
    try:
        # Extract userId from query parameters
        # Expect a call like: GET /listusers?userId=owner@example.com
        query_params = event.get('queryStringParameters', {})
        owner_user_id = query_params.get('userId', None)
        
        if not owner_user_id:
            return response(400, {"error": "userId is required as a query parameter"})

        users_table = dynamodb.Table('Users')
        
        # Perform a scan and filter by userId
        # Assuming each item has an attribute 'userId' that matches the owner’s email or ID
        scan_response = users_table.scan(
            FilterExpression=Attr('userId').eq(owner_user_id)
        )

        if 'Items' not in scan_response or len(scan_response['Items']) == 0:
            return response(200, {"message": "No users found", "users": []})

        users_list = []
        for item in scan_response['Items']:
            # Each item should have faceId, name, email, and photoKey
            user_name = item.get('name', 'Unknown')
            user_email = item.get('email', 'No Email')
            photo_key = item.get('photoKey', None)

            photo_url = None
            if photo_key:
                # Generate a pre-signed URL for the user's photo
                photo_url = s3.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': S3_BUCKET, 'Key': photo_key},
                    ExpiresIn=3600
                )

            # Also include userId and faceId if needed by frontend
            face_id = item.get('faceId')
            users_list.append({
                "Name": user_name,
                "Email": user_email,
                "PhotoURL": photo_url,
                "userId": owner_user_id,
                "faceId": face_id
            })

        return response(200, {"message": "Users retrieved successfully", "users": users_list})
    
    except Exception as e:
        # Error response
        print("Error:", str(e))
        return response(500, {"error": str(e)})

def log_event(eventType, details):
    log_table.put_item(
        Item={
            "eventType": eventType,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **details
        }
    )

def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": json.dumps(body)
    }
