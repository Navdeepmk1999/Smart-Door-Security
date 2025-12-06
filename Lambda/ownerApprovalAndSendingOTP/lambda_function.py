import boto3
import json
import random
from datetime import datetime, timezone
from time import sleep



# Initialize DynamoDB tables and SES client
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
log_table = dynamodb.Table('SmartDoorLogs')
table = dynamodb.Table('VisitorRequestDetails')
ses = boto3.client('ses', region_name='us-west-2')
ssm = boto3.client('ssm')

# Logging function
def log_event(eventType, details):
    log_table.put_item(
        Item={
            "eventType": eventType,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **details
        }
    )

# Main handler
def lambda_handler(event, context):
    for record in event['Records']:
        
        body = json.loads(record['body'])
        print(body)
        

    face_id = body.get("id")
    approve = body.get("approved")
    doorId = body.get("doorId")
    userID = body.get("userID")

    print(userID)
    

    if not face_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "faceId is required."})
        }
    
    # Fetch the visitor from DynamoDB
    response = table.get_item(Key={"faceId": face_id})
    visitor = response.get("Item")

    if not visitor:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Request not found."})
        }
    
        
    if approve:  # Handle approval
        # Generate OTP
        otp = str(random.randint(100000, 999999))
        
        # Update DynamoDB with approval and OTP
        table.update_item(
            Key={"faceId": face_id},
            UpdateExpression="SET #statusAlias = :status, OTP = :otp",
            ExpressionAttributeNames={
                "#statusAlias": "status"
            },
            ExpressionAttributeValues={
                ":status": "Approved",
                ":otp": otp
            }
        )
        
        ssm.put_parameter(
                Name=doorId,
                Value="ENTEROPT",
                Overwrite=True
            )
        # Send OTP via email
        try:
            print("sending otp")
            ses.send_email(
                Source="navdeepmkn@gmail.com",
                Destination={"ToAddresses": [visitor["email"]]},
                Message={
                    "Subject": {"Data": "Smart Door OTP"},
                    "Body": {"Text": {"Data": f"Your OTP is: {otp}, please click OPEN DOOR and enter your OTP."}}
                }
            )
            # Log event: Approval and OTP sent
            log_event("APPROVAL", {
                "visitorId": face_id,
                "name": visitor["name"],
                "email": visitor["email"],
                "status": "Approved",
                "details": {"otpSent": True}
            })
        except Exception as e:
            # Log event: Email sending failed
            log_event("ERROR", {
                "visitorId": face_id,
                "name": visitor["name"],
                "email": visitor["email"],
                "details": {"error": str(e)}
            })
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Failed to send email.", "details": str(e)})
            }

        message = "Visitor approved and OTP sent."
    else:  # Handle rejection
    
        ssm.put_parameter(
                Name=doorId,
                Value="ACESSDENIED",
                Overwrite=True
            )
        # Update DynamoDB with rejection
        table.update_item(
            Key={"faceId": face_id},
            UpdateExpression="SET #statusAlias = :status",
            ExpressionAttributeNames={
                "#statusAlias": "status"
            },
            ExpressionAttributeValues={":status": "Rejected"}
        )
        
        # Log event: Rejection
        log_event("APPROVAL", {
            "visitorId": face_id,
            "name": visitor["name"],
            "email": visitor["email"],
            "status": "Rejected"
        })
        
        message = "Visitor rejected."
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": message})
    }
