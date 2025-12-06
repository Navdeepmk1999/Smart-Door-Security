import json
import boto3
from datetime import datetime, timezone


# Initialize AWS services
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
log_table = dynamodb.Table('SmartDoorLogs')
ssm = boto3.client('ssm')


def lambda_handler(event, context):
    print(event)
    
    
    parameter_name = event.get('queryStringParameters', {}).get('doorId', 'main')
    print(parameter_name)
    try:
        # Retrieve the door status from Parameter Store
        response = ssm.get_parameter(Name=parameter_name)
        status = response['Parameter']['Value']
        
        # Define the activity based on the door status
        activity = "Door is Opened" if status.lower() == "unlocked" else "Door is Closed"

        # Log the event
        log_event(
            eventType="DOOR_STATUS",
            details={
                "status": status,
                "details": activity
            }
        )

        # Return the response
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
             "body": json.dumps({"STATE": status}) 
        }
         # Encode the inner JSON for "body"
    except Exception as e:
        # Log the error
        log_event(
            eventType="ERROR",
            details={
                "error": str(e),
                "context": "Failed to retrieve or process door status"
            }
        )
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal Server Error"})
        }

def log_event(eventType, details):
    """
    Log an event in the SmartDoorLogs DynamoDB table.
    """
    log_table.put_item(
        Item={
            "eventType": eventType,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **details
        }
    )
