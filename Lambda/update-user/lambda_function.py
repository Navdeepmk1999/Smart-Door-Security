import json
import boto3
import base64
from datetime import datetime, timezone
import re

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
users_table = dynamodb.Table('Users')

s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')

S3_BUCKET = "my-user-photos-bucket"
REKOGNITION_COLLECTION = "rekVideoBlog"

def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": json.dumps(body)
    }

def lambda_handler(event, context):
    try:
        body = event
        faceId = body.get('faceId')
        name = body.get('name')
        
        print(faceId)

        if not faceId:
            return response(400, {"error": "faceId is required"})

        # Fetch the existing user item
        get_response = users_table.get_item(Key={'faceId': faceId})
        if 'Item' not in get_response:
            return response(404, {"error": "User not found"})

        item = get_response['Item']

        # Prepare UpdateExpression and ExpressionAttributeValues
        update_expr = []
        expr_values = {}

        # Update name if provided
        if 'name' in body and body['name']:
            update_expr.append("name = :n")
            expr_values[':n'] = body['name']

        # Update email if provided
        if 'email' in body and body['email']:
            update_expr.append("email = :e")
            expr_values[':e'] = body['email']

        # Check if a new photo is provided
        photo_key = item.get('photoKey', None)
        if 'photo' in body and body['photo']:
            # Process new photo
            image_data = body['photo'].split(",")[1]
            image_bytes = base64.b64decode(image_data)
            # We can delete old photo if needed:
            if photo_key:
                # Attempt to delete old photo
                try:
                    s3.delete_object(Bucket=S3_BUCKET, Key=photo_key)
                except Exception as e:
                    print("Error deleting old photo:", e)

            # Upload new photo
            new_photo_key = f"{faceId}.png"
            s3.put_object(
                Bucket=S3_BUCKET,
                Body=image_bytes,
                Key=new_photo_key,
                ContentType='image/png'
            )

            # Re-index face if required
            rekognition.index_faces(
                CollectionId=REKOGNITION_COLLECTION,
                Image={'S3Object': {'Bucket': S3_BUCKET, 'Name': new_photo_key}},
                ExternalImageId=faceId,
                DetectionAttributes=['ALL']
            )

            update_expr.append("photoKey = :p")
            expr_values[':p'] = new_photo_key

        if not update_expr:
            # No fields to update
            return response(200, {"message": "No changes made"})

        update_expression = "SET " + ", ".join(update_expr)

        users_table.update_item(
            Key={'faceId': faceId},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expr_values
        )

        return response(200, {"message": "User updated successfully"})

    except Exception as e:
        print("Error:", str(e))
        return response(500, {"error": str(e)})
