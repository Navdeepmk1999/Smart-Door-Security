import boto3
import json

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
log_table = dynamodb.Table('SmartDoorLogs')

def lambda_handler(event, context):
    try:

        response = log_table.scan()
        logs = response.get('Items', [])

        # Calculate analytics
        unlocks = sum(1 for log in logs if log.get("eventType") == "DOOR_UNLOCKED")
        approvals = sum(1 for log in logs if log.get("eventType") == "APPROVAL")
        rejections = sum(1 for log in logs if log.get("status") == "Rejected")
        visitors = sum(1 for log in logs if log.get("eventType") == "ACCESS_REQUESTED")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET"
            },
            "body": json.dumps({
                "unlocks": unlocks,
                "approvals": approvals,
                "rejections": rejections,
                "visitors": visitors
            })
        }

    except Exception as e:
        print(f"Error calculating analytics: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to calculate analytics.", "details": str(e)})
        }
