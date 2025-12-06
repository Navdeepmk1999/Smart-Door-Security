import json
import boto3
import base64
kinesis_client = boto3.client('kinesis')


def lambda_handler(event, context):
    for record in event['Records']:
        raw_data = base64.b64decode(record['kinesis']['data'])
        kinesis_client.put_record(
            StreamName='BackDoor_stream',
            Data=raw_data,
            PartitionKey='partitionKey'
        )
    return {
        'statusCode': 200,
        'body': 'Data forwarded successfully'
    }
