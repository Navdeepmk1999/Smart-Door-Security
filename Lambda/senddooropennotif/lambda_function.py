import boto3
import json
import os

# Initialize SES client
ses_client = boto3.client('ses')


# Environment Variables
SENDER_EMAIL = 'navdeepmkn@gmail.com'
RECIPIENT_EMAIL = 'kbhuvanchand@gmail.com'
ssm = boto3.client('ssm')

# Parameter Store for door status
parameter_name = '/door/RekognitionVideoBlog-Stream/status'

def send_email():
    subject = "Door has been UNLOCKED"
    body = """
    Alert: The door has been UNLOCKED.
    Please take necessary action.
    """
    
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
    print(f"Email sent: {response}")
    

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        response = ssm.get_parameter(Name=parameter_name)
        status = response['Parameter']['Value']
        
        
        if status == "DOORUNLOCKEDOPT" :
            print("State is UNLOCKED. Sending email...")
            send_email()
        else:
            print(f"State is {status}. No action taken.")
            
    except Exception as e:
        print(f"Error: {e}")
