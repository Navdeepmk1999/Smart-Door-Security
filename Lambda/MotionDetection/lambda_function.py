import json
import sys
import cv2
import boto3
import base64
import time
import numpy as np


# Initialize global variables for cooldown
LAST_DETECTION_TIME = 0
COOLDOWN_PERIOD = 10  # seconds


def lambda_handler(event, context):
    global LAST_DETECTION_TIME
    
    # Initialize Kinesis Video Streams client
    kvs_client = boto3.client('kinesisvideo')
    kvs_data_pt = kvs_client.get_data_endpoint(
        StreamARN='arn:aws:kinesisvideo:us-west-2:692859952170:stream/LiveRekognitionVideoAnalysisBlog/1734183800076',
        APIName='GET_MEDIA'
    )
    
    print("Kinesis Video Data Endpoint:", kvs_data_pt)
    
    # Decode the incoming Kinesis data
    record = event['Records'][0]['kinesis']['data']
    data = json.loads(base64.b64decode(record))
    print("Decoded Event Data:", data)
    
    end_pt = kvs_data_pt['DataEndpoint']
    print(end_pt)
    kvs_video_client = boto3.client('kinesis-video-media', endpoint_url=end_pt, region_name='us-west-2')
    frag_num = data["InputInformation"]["KinesisVideo"]["FragmentNumber"]
    print("gra",frag_num)
    
    start_selector = {
        'StartSelectorType': 'NOW'
    }
    
    # start_selector = {
    # 'StartSelectorType': 'FRAGMENT_NUMBER',
    # 'AfterFragmentNumber': frag_num
    # }

    
    
    
    # Get the media stream starting after the specified fragment number
    kvs_stream = kvs_video_client.get_media(
        StreamARN='arn:aws:kinesisvideo:us-west-2:692859952170:stream/LiveRekognitionVideoAnalysisBlog/1734183800076',
        StartSelector=start_selector
    )
    
    
    print("Kinesis Video Stream Retrieved")
    
    with open('/tmp/streams.mkv', 'wb') as f:
        print("Reading stream data...")
        streamBody = kvs_stream['Payload'].read(1024 * 2048)
        f.write(streamBody)
    
    # Initialize OpenCV Video Capture
    cap = cv2.VideoCapture('/tmp/streams.mkv')
    
    ret, prev_frame = cap.read()
    motion_detected = False
    person_detected = False
    detected_frame = None
    
    while True:
        ret, curr_frame = cap.read()
        if not ret:
            break
        
        # Convert frames to grayscale
        gray_prev = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        gray_curr = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate absolute difference
        diff = cv2.absdiff(gray_prev, gray_curr)
        
        # Threshold the difference
        _, thresh = cv2.threshold(diff, 50, 255, cv2.THRESH_BINARY)
        
        # Count non-zero pixels
        motion_pixels = np.count_nonzero(thresh)
        
        if motion_pixels > 2000:  # Adjust threshold based on environment
            print("Motion detected!")
            motion_detected = True
            detected_frame = curr_frame.copy()
            break
        
        prev_frame = curr_frame
    
    cap.release()
    
    if motion_detected:
        current_time = time.time()
        if current_time - LAST_DETECTION_TIME < COOLDOWN_PERIOD:
            print("Cooldown period active. Skipping detection.")
            return {
                'statusCode': 200,
                'body': json.dumps('Cooldown active. No action taken.')
            }
        
        # Option 1: Use Amazon Rekognition for Person Detection
        rekognition_client = boto3.client('rekognition')
        _, buffer = cv2.imencode('.jpg', detected_frame)
        image_bytes = buffer.tobytes()
        
        response = rekognition_client.detect_labels(
            Image={'Bytes': image_bytes},
            MaxLabels=10,
            MinConfidence=70
        )
        
        print("Rekognition Labels:", response['Labels'])
        
        # Check if any label corresponds to a person
        for label in response['Labels']:
            if label['Name'] == 'Person' and label['Confidence'] >= 70:
                person_detected = True
                break
        
        if person_detected:
            print("Person detected in the frame!")
            s3_client = boto3.client('s3')
            timestamp = int(time.time() * 1000)
            file_name = f"person_entry_{timestamp}.jpg"
            cv2.imwrite('/tmp/person_frame.jpg', detected_frame)
            s3_client.upload_file(
                '/tmp/person_frame.jpg',
                'motiondetectionlogs',
                file_name
            )
            print('Person frame uploaded to S3.')
            
            # Update the last detection time
            LAST_DETECTION_TIME = current_time
        else:
            print("No person detected in the motion event.")
    else:
        print("No motion detected.")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Motion and person detection completed.')
    }
