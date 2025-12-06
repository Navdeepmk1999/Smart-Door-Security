import boto3
import base64
import json
from datetime import datetime, timezone
import time

# Initialize AWS resources
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
log_table = dynamodb.Table('SmartDoorLogs')
table = dynamodb.Table('VisitorRequestDetails')
rekognition = boto3.client('rekognition')
ssm = boto3.client('ssm')
OWNER_EMAIL='navdeepmkn@gmail.com'

# Function to log events to DynamoDB
def log_event(eventType, details):
    log_table.put_item(
        Item={
            "eventType": eventType,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **details
        }
    )

def send_otp_to_owner(visitor_name, visitor_email):
    subject = "Alert: Visitor Denied Access"
    body = (
        f"The visitor with the following details failed OTP verification multiple times:\n\n"
        f"Name: {visitor_name}\n"
        f"Email: {visitor_email}\n\n"
        "Please investigate the situation."
    )

    ses.send_email(
        Source=OWNER_EMAIL,
        Destination={"ToAddresses": [OWNER_EMAIL]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body}}
        }
    )
    
    

def lambda_handler(event, context):
    try:
        # Extract input data from the event
        otp = event.get("otp")
        image_data = event.get('image')
        doorId = event.get('doorId') 
        userId = event.get('userId') 
        
        print(otp)
        print(doorId)
        print(userId)

        if not otp or not image_data:
            raise ValueError("Missing required fields: 'otp', 'image', or 'faceId'")

        # Decode base64 image data
        image_bytes = base64.b64decode(image_data.split(",")[1])
        
        collection_id="visitor2"
        response = rekognition.search_faces_by_image(
            CollectionId=collection_id,
            Image={'Bytes': image_bytes},
            MaxFaces=1  # Get the best match only
        )
        
               # Check if any face matches were found
        if not response.get('FaceMatches'):
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "No matching face found in the collection"})
            }

        # Extract the faceId of the best match
        face_match = response['FaceMatches'][0]
        face_id = face_match['Face']['FaceId']
        similarity = face_match['Similarity']
        print(face_id)

        # Fetch the visitor details from DynamoDB
        response = table.get_item(Key={'faceId': face_id})
        visitor = response.get("Item")
        print("visitor",visitor)
        
        if not visitor:
            log_event("ERROR", {"details": f"FaceId {face_id} not found in database"})
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "FaceId not found in database"})
            }

        # Validate OTP
        print(otp)
        print(visitor.get("OTP"))
        if visitor.get("OTP") == otp:
            ssm.put_parameter(
                Name=doorId,
                Value="DOORUNLOCKEDOPT",
                Overwrite=True
            )
            time.sleep(10)
            print("changing to locked" )
            ssm.put_parameter(
                Name=doorId,
                Value="DOORLOCKED",
                Overwrite=True
            )
            
            
            # Removing the face from the collection
            try:
                rekognition.delete_faces(
                    CollectionId=collection_id,
                    FaceIds=[face_id]
                )
                print(f"Face with FaceId {face_id} removed from the collection {collection_id}")
            except Exception as e:
                log_event("ERROR", {"details": f"Failed to remove FaceId {face_id}: {str(e)}"})
                print(f"Error removing face: {str(e)}")
            
            
            
            
            log_event("DOOR_UNLOCKED", {
                "faceId": face_id,
                "name": visitor.get("name"),
                "email": visitor.get("email"),
                "details": {"method": "Face and OTP verification"}
            })
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "OTP validated. Door unlocked."})
            }
        else:
            # Increment failed attempts
            failed_attempts = visitor.get("failedAttempts", 0) + 1
            table.update_item(
                Key={'faceId': face_id},
                UpdateExpression="SET failedAttempts = :val",
                ExpressionAttributeValues={":val": failed_attempts}
            )
            
            MAX_ATTEMPTS=3
            if failed_attempts >= MAX_ATTEMPTS:
                send_otp_to_owner(visitor.get("name"), visitor.get("email"))
                log_event("MAX_ATTEMPTS_REACHED", {
                    "faceId": face_id,
                    "name": visitor.get("name"),
                    "email": visitor.get("email"),
                    "details": {"failed_attempts": failed_attempts}
                })

            ssm.put_parameter(
                Name=doorId,
                Value="ACCESSDENIED",
                Overwrite=True
            )
            log_event("INVALID_OTP", {
                "faceId": face_id,
                "name": visitor.get("name"),
                "email": visitor.get("email"),
                "details": {"provided_otp": otp, "stored_otp": visitor.get("OTP"), "failed_attempts": failed_attempts}
            })
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid OTP."})
            }


    except ValueError as e:
        log_event("ERROR", {"details": str(e)})
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }
