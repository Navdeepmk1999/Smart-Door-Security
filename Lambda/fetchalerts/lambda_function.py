import boto3
import json

# Initialize AWS client
s3 = boto3.client('s3')

# Define S3 bucket and file
BUCKET_NAME = "visitor-bucket-1"
ALERTS_FILE = "alerts.json"

def lambda_handler(event, context):
    try:
        # Fetch the alerts file from S3
        response = s3.get_object(Bucket=BUCKET_NAME, Key=ALERTS_FILE)
        alerts = json.loads(response['Body'].read().decode('utf-8'))
        
        # Return the alerts
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Alerts retrieved successfully", "alerts": alerts})
        }
    
    except Exception as e:
        # Error response
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
