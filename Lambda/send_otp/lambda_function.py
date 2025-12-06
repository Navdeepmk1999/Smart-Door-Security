import boto3
import base64
import json
from datetime import datetime, timezone



# Initialize AWS resources
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
log_table = dynamodb.Table('SmartDoorLogs')
table = dynamodb.Table('VisitorRequestDetails')
s3_service = boto3.client('s3')
rekognition = boto3.client('rekognition')

# Logging function
def log_event(eventType, details):
    log_table.put_item(
        Item={
            "eventType": eventType,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **details
        }
    )
    
def send_otp_to_owner(doorId):
    subject = "Alert: Visitor Request Access"
    body = (
        f"There is a visitor at your Door {doorId}. Please open the dashboard and take necessary action \n\n"
    )    
    
# Lambda handler
def lambda_handler(event, context):
    try:
        print(event)
        name = event.get('name')
        email = event.get('email')
        image_data = event.get('image')  # Base64 encoded image
        doorId=event.get('doorId')
        userId=event.get('userId')
        print(userId)
        print(doorId)
        print(name)

        if not name or not email or not image_data:
            raise ValueError("Missing required fields: 'name', 'email', or 'image'.")

        # Define constants
        bucket_name = "visitor-bucket-1"
        initial_object_key = 'frame.jpg'  # Temporary name for the uploaded file

        # Decode the Base64 image
        image_data = image_data.split(",")[1]
        image_bytes = base64.b64decode(image_data)
        
        print(image_bytes)
        print(bucket_name)
        print(initial_object_key)

        # Upload image to S3 with a temporary key
        s3_service.put_object(
            Bucket=bucket_name,
            Body=image_bytes,
            Key=initial_object_key,
            ContentType='image/png'
        )

        # Index the face using Rekognition
        collection_id = 'visitor2'
        rekognition_index_response = rekognition.index_faces(
            CollectionId=collection_id,
            Image={'S3Object': {'Bucket': bucket_name, 'Name': initial_object_key}}
        )

        # Extract the FaceId from the response
        face_id = None
        for faceRecord in rekognition_index_response['FaceRecords']:
            face_id = faceRecord['Face']['FaceId']
        
        print(face_id)
        if not face_id:
            raise Exception("No face detected. Cannot proceed further.")

        # Rename the S3 object using the FaceId
        new_object_key = f"{face_id}.png"
        s3_service.copy_object(
            Bucket=bucket_name,
            CopySource={'Bucket': bucket_name, 'Key': initial_object_key},
            Key=new_object_key
        )
        s3_service.delete_object(Bucket=bucket_name, Key=initial_object_key)

        # Construct the S3 file location
        s3_file_location = f"s3://{bucket_name}/{new_object_key}"

        # Save data to DynamoDB
        table.put_item(
            Item={
                "faceId": face_id,
                "name": name,
                "email": email,
                "imageLocation": s3_file_location,
                "status": "Pending",
                "doorId": doorId,
                "userId":userId
                
            }
        )
        send_otp_to_owner(doorId)
        

        # Log success events
        log_event("FACE_INDEXED", {
            "faceId": face_id,
            "name": name,
            "email": email,
            "imageLocation": s3_file_location
        })

        log_event("DYNAMODB_INSERT", {
            "faceId": face_id,
            "name": name,
            "email": email,
            "status": "Pending"
        })

        print(f"FaceId: {face_id}")
        print(f"Image stored at: {s3_file_location}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Face indexed and data saved successfully.",
                "FaceId": face_id,
                "ImageLocation": s3_file_location
            })
        }

    except Exception as e:
        # Log error event
        log_event("ERROR", {
            "details": {
                "error": str(e),
                "input": event.get('body', {})
            }
        })

        # Return error response
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
