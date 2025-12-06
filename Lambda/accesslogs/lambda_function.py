import boto3
import json

# Initialize AWS client
s3 = boto3.client('s3')

# Define S3 bucket
LOGS_BUCKET = "visitor-bucket-1"

def lambda_handler(event, context):
    try:
        # List all log files in the bucket
        response = s3.list_objects_v2(Bucket=LOGS_BUCKET)
        if 'Contents' not in response:
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No logs found", "logs": []})
            }
        
        # Fetch and aggregate all logs
        logs = []
        for obj in response['Contents']:
            if obj['Key'].endswith('.json'):  # Assuming log files are JSON
                log_file = s3.get_object(Bucket=LOGS_BUCKET, Key=obj['Key'])
                file_content = json.loads(log_file['Body'].read().decode('utf-8'))
                logs.extend(file_content)  # Add logs from each file
        
        # Sort logs by timestamp (most recent first)
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Return the aggregated logs
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Logs retrieved successfully", "logs": logs})
        }
    
    except Exception as e:
        # Error response
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
