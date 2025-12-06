import json
import boto3
from urllib.parse import unquote_plus

def lambda_handler(event, context):
    s3_client = boto3.client('s3')
    bucket_name = 'motiondetectionlogs'
    try:
        # List objects in the bucket, sorted by LastModified descending
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix='person_entry_',
            MaxKeys=200  # Adjust as needed
        )
        
        if 'Contents' not in response:
            return {
                'statusCode': 200,
                'body': json.dumps({'images': []})
            }
        
        images = []
        for obj in sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True):
            key = obj['Key']
            # Generate a pre-signed URL valid for 1 hour
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': key},
                ExpiresIn=3600  # seconds
            )
            images.append({
                'key': key,
                'url': url,
                'last_modified': obj['LastModified'].isoformat()
            })
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'  # Adjust as needed for security
            },
            'body': json.dumps({'images': images})
        }
        
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to list images.'})
        }
