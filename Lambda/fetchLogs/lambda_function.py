import boto3
import json
from boto3.dynamodb.conditions import Attr
from decimal import Decimal

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
log_table = dynamodb.Table('SmartDoorLogs')

def convert_decimal(obj):
    """
    Recursively converts DynamoDB Decimal objects to float or int.
    """
    if isinstance(obj, list):
        return [convert_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        # Convert to int if the Decimal is integral; otherwise, convert to float
        return int(obj) if obj % 1 == 0 else float(obj)
    else:
        return obj

def lambda_handler(event, context):
    # Safely retrieve query string parameters
    query_params = event.get('queryStringParameters') or {}
    start_time = query_params.get('startTime')
    end_time = query_params.get('endTime')

    print(f"Received event: {json.dumps(event)}")
    logs = []

    try:
        # Fetch logs based on query parameters
        filter_expression = None
        if start_time and end_time:
            filter_expression = Attr("timestamp").between(start_time, end_time)
            print(f"Fetching logs between {start_time} and {end_time}")

        # Handle pagination
        last_evaluated_key = None
        while True:
            scan_args = {"FilterExpression": filter_expression} if filter_expression else {}
            if last_evaluated_key:
                scan_args["ExclusiveStartKey"] = last_evaluated_key

            response = log_table.scan(**scan_args)
            logs.extend(response.get('Items', []))
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

        # Convert logs to JSON-serializable format
        logs = convert_decimal(logs)
        print(logs)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET"
            },
            "body": json.dumps(logs)
        }

    except Exception as e:
        print(f"Error fetching logs: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to fetch logs.", "details": str(e)})
        }
