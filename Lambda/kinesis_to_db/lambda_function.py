import json
import base64
import boto3
from datetime import datetime, timezone

# Initialize AWS resources
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
log_table = dynamodb.Table('SmartDoorLogs')
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

def lambda_handler(event, context):
    try:
        print(event['Records'][0])
        event_source_arn = event['Records'][0]['eventSourceARN']
        door_id = event_source_arn.split('/')[-1]
        
        parameter_name = f'/door/{door_id}/status'
        
        # Decode and parse the Kinesis data record
        record = event['Records'][0]['kinesis']['data']
        data = json.loads(base64.b64decode(record))
        print("Received data:", data)
        
        # Extract FaceSearchResponse from the data
        face_search_response = data.get('FaceSearchResponse', [])
        
        if not face_search_response:
            # No face detected
            ssm.put_parameter(
                Name=parameter_name,
                Value="Nofacedetected",
                Type='String',
                Overwrite=True
            )
            print(f"No face detected for door: {door_id}")
            return {"statusCode": 200, "body": "No face detected"}
        
        # Check for matched faces
        matched_faces = face_search_response[0].get('MatchedFaces', [])
        if matched_faces:
            # Update SSM parameter to DOORUNLOCKED
            ssm.put_parameter(
                Name=parameter_name,
                Value="DOORUNLOCKED",
                Type='String',
                Overwrite=True
            )
            log_event("DOOR_UNLOCKED",{"details": f"{parameter_name}DOOR has been Unlocked"})
            print(f"Door {door_id} unlocked (recognized face)")

            return {"statusCode": 200, "body": "Door unlocked"}
        else:
            print(f"New face detected at door {door_id}")
            
            # Check current state
            response = ssm.get_parameter(Name=parameter_name)
            status = response['Parameter']['Value']
            print("Current status:", status)
            
            # If door is locked/unlocked or no face detected previously, send access request
            if status in ["DOORLOCKED", "DOORUNLOCKED", "Nofacedetected"]:
                ssm.put_parameter(
                    Name=parameter_name,
                    Value="ACESSREQUESTSENT",
                    Type='String',
                    Overwrite=True
                )
                log_event("ACCESS_REQUESTED",{"details": f" for {parameter_name} DOOR ACCESS HAS BEEN REQUESTED"})

                print(f"Access request sent for door {door_id}")
            
            return {"statusCode": 200, "body": "Access requested"}
    
    except Exception as e:
        # Log error event if needed
        print("Error:", str(e))
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
