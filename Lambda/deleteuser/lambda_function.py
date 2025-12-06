import json
import boto3

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
        faceId = event.get('faceId')

        if not faceId:
            return response(400, {"error": "faceId is required"})

        # Retrieve the user
        get_response = users_table.get_item(Key={'faceId': faceId})
        if 'Item' not in get_response:
            return response(404, {"error": "User not found"})

        item = get_response['Item']
        photo_key = item.get('photoKey')

        # Delete from DynamoDB
        users_table.delete_item(Key={'faceId': faceId})

        # Delete from S3 if photo_key exists
        if photo_key:
            try:
                s3.delete_object(Bucket=S3_BUCKET, Key=photo_key)
            except Exception as s3_error:
                print("Error deleting photo from S3:", s3_error)

        # Delete face from Rekognition
        # faceId here is the partition key and also used as ExternalImageId. 
        # If you need the Rekognition FaceId, you should have stored it when adding the user.
        # Assuming faceId stored is actually the Rekognition FaceId for simplicity:
        try:
            rekognition.delete_faces(
                CollectionId=REKOGNITION_COLLECTION,
                FaceIds=[faceId]
            )
        except Exception as rek_error:
            print("Error deleting face from Rekognition:", rek_error)

        return response(200, {"message": "User deleted successfully"})
    
    except Exception as e:
        print("Error:", str(e))
        return response(500, {"error": str(e)})
