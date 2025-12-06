import boto3
import base64
import json
import uuid
from datetime import datetime

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# DynamoDB and S3 configurations
TABLE_NAME = 'unsual-activity'
BUCKET_NAME = 'unsual-activity-log'
SENDER_EMAIL = 'navdeepmkn@gmail.com'  # Replace with your verified SES email
RECIPIENT_EMAIL = 'navdeepmkn@gmail.com'  # Replace with the recipient's email
ses_client = boto3.client('ses')



def lambda_handler(event, context):
    image_data=event.get("image")
    # Decode the Base64 image
    image_data = image_data.split(",")[1]  # Remove the Base64 prefix if present
    image_bytes = base64.b64decode(image_data)

    # Generate a unique key for the image
    image_key = f"captured-images/{uuid.uuid4()}.png"

    # Upload the image to S3
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=image_key,
        Body=image_bytes,
        ContentType='image/png'
    )

    # Prepare metadata for DynamoDB
    table = dynamodb.Table(TABLE_NAME)
    item = {
        "faceId": str(uuid.uuid4()),  # Unique identifier
        "imageLocation": f"s3://{BUCKET_NAME}/{image_key}",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    
    # Store metadata in DynamoDB
    table.put_item(Item=item)
    
    # Send an email notification
    subject = "Unusual Activity Detected at Your Door"
    body = (
        f"An unusual activity was detected at your door on {item['timestamp']}.\n"
        "Please check your door immediately."
    )
    
    # sending an mail to owner!!
    send_email(subject, body)
    

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Image stored successfully", "imageLocation": item["imageLocation"]})
    }


def send_email(subject, body):
    """Send an email using AWS SES."""
    response = ses_client.send_email(
        Source=SENDER_EMAIL,
        Destination={
            'ToAddresses': [RECIPIENT_EMAIL]
        },
        Message={
            'Subject': {
                'Data': subject
            },
            'Body': {
                'Text': {
                    'Data': body
                }
            }
        }
    )
    return response    