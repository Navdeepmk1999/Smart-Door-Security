import boto3
import base64
import uuid
import json
from datetime import datetime, timezone
import re



# Initialize AWS resources
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
log_table = dynamodb.Table('SmartDoorLogs')
users_table = dynamodb.Table('Users')

# AWS Clients
s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')

# Updated S3 bucket name as mentioned by you
bucket_name = "my-user-photos-bucket"
REKOGNITION_COLLECTION = "rekVideoBlog"

# Logging function
def log_event(eventType, details):
    log_table.put_item(
        Item={
            "eventType": eventType,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **details
        }
    )

# Sanitize ExternalImageId
def sanitize_external_image_id(name):
    return re.sub(r'[^a-zA-Z0-9_.\-:]', '_', name)

def lambda_handler(event, context):
    try:
        print("Received event:", event)
        body = json.loads(event['body'])
        name = body.get('name')
        email = body.get('email')
        image_base64 = body.get('photo')
        userId = body.get('userId')

        if not name or not email or not image_base64:
            raise ValueError("Missing required fields: 'name', 'email', or 'photo'")
        
        
        image_data = image_base64.split(",")[1]
        image_bytes = base64.b64decode(image_data)
        
        initial_object_key = 'frame.jpg'

        # Upload the image to S3
        s3_response = s3.put_object(
            Bucket=bucket_name,
            Body=image_bytes,
            Key=initial_object_key,
            ContentType='image/png'
        )
        
        rekognition_response = rekognition.index_faces(
            CollectionId=REKOGNITION_COLLECTION,
            Image={'S3Object': {'Bucket': bucket_name, 'Name': initial_object_key}}
        )
        
                # Extract the FaceId from the response
        face_id = None
        for faceRecord in rekognition_response['FaceRecords']:
            face_id = faceRecord['Face']['FaceId']

        if not face_id:
            raise Exception("No face detected. Cannot proceed further.")

        # Extract the FaceId
        if not rekognition_response['FaceRecords']:
            raise ValueError("No face detected in the uploaded image")
            
        new_object_key = f"{face_id}.png"
        s3.copy_object(
            Bucket=bucket_name,
            CopySource={'Bucket': bucket_name, 'Key': initial_object_key},
            Key=new_object_key
        )
        s3.delete_object(Bucket=bucket_name, Key=initial_object_key)   
        
        s3_file_location = f"s3://{bucket_name}/{new_object_key}"

        # Insert user details into UsersTable
        users_table.put_item(
            Item={
                "faceId": face_id,
                "name": name,
                "email": email,
                "imageLocation": s3_file_location,
                "userId": userId
            }
        )

        # Log success event
        log_event("USER_ADDED", {
            "name": name,
            "email": email,
            "faceId": face_id,
            "details": {"method": "Face Registration"}
        })

        # Return success response
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps({
                "message": "User added successfully",
                "FaceId": face_id,
                "ImageKey": new_object_key,
                "S3Bucket": bucket_name
            })
        }

    except Exception as e:
        log_event("ERROR", {
            "details": {
                "error": str(e),
                "input": event.get('body', {})
            }
        })
        print("Error:", str(e))  # Debug log

        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps({"error": str(e)})
        }
