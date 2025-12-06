import boto3
import json
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
log_table = dynamodb.Table('SmartDoorLogs')

def lambda_handler(event, context):
    event_type = event.get('pathParameters', {}).get('eventType')

    if not event_type:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "eventType is required in the path."})
        }

    try:
        response = log_table.query(
            KeyConditionExpression=Key("eventType").eq(event_type)
        )

        items = response.get('Items', [])
        if not items:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": f"No logs found for eventType: {event_type}"})
            }

        current_timestamp = datetime.now(timezone.utc).isoformat()
        for item in items:
            item['queriedAt'] = current_timestamp  # Add the timestamp to each log entry


        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET"
            },
            "body": json.dumps(items)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to fetch logs.", "details": str(e)})
        }
