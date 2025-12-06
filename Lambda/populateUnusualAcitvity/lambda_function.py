import boto3
import json
import base64


dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('unsual-activity')  # Replace 'Users' with your table name
s3=boto3.client('s3')


def lambda_handler(event, context):
    try:
        response = table.scan()
        users = response['Items']
        
        result = []

        for user in users:
            # Retrieve image bytes if the imageLocation exists
            if "imageLocation" in user:
                # Extract bucket name and key from the S3 location
                s3_path = user["imageLocation"].replace("s3://", "")
                bucket_name, key = s3_path.split("/", 1)
                
                # Get the image from S3
                s3_response = s3.get_object(Bucket=bucket_name, Key=key)
                image_bytes = base64.b64encode(s3_response['Body'].read()).decode('utf-8')
            else:
                image_bytes = None
            
            # Append user details with image bytes
            result.append({
                "status": user["timestamp"],
                "image": image_bytes
            })

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(result)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"error": str(e)})
        }
