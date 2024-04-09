import json
import boto3
import datetime
from datetime import datetime
import time,traceback
import pandas as pd
import os.path
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

def lambda_handler(event, context):
    try:
        def convertToMil(value):
            dt_obj = datetime.strptime(str(value),'%Y-%m-%d %H:%M:%S')
            result = int(dt_obj.timestamp() * 1000)
            return result
        client = boto3.client('logs')
        s3_client = boto3.client('s3')
        # last 24 hr in millisecond
        time_millisec = 86400000 
        
        currentdateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        getCurrentMilsec = convertToMil(str(currentdateTime))
        getYesterdayMilsec = getCurrentMilsec - time_millisec
        
        # The below is the query to filter the particular Alarm. Edit the alarm name in the query as per your Alarm name.
        # https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html
        demoec2_cpu__critical_query = "fields @timestamp, detail.alarmName, detail.state.value, @message | filter detail.state.value in ['ALARM']"
        
        # create similar query for each alarm which we need to monitor for past 24hr and include in the below list.
        queryString_list = [demoec2_cpu__critical_query]
        final_data = []
        
        for queryString in queryString_list:
            # The below code queries the cloudwatch log group where the alarm datas are stored.
            response = client.start_query(
                logGroupName= "/aws/events/alarms/",
                startTime=getYesterdayMilsec,
                endTime=getCurrentMilsec,
                queryString=queryString
            )
            data = json.dumps(response, indent=2)
            jsonResult = json.loads(data)
            time.sleep(5)
            queryResponse = client.get_query_results(queryId=jsonResult['queryId'])
            queryResponsedata = json.dumps(queryResponse, indent=2)
            queryResponsejsonResult = json.loads(queryResponsedata)

            # the below code snippet is to parge the response 
            for each_result_list in reversed(queryResponsejsonResult["results"]):
                each_result =  json.loads(each_result_list[3]['value'])
                each_state_value = each_result['detail']['state']['value']
                instance_id = each_result['detail']['configuration']['metrics'][0]['metricStat']['metric']['dimensions']['InstanceId']
                instance_name = each_result['detail']['configuration']['description']
                metric_name = each_result['detail']['configuration']['metrics'][0]['metricStat']['metric']['name']
                alarm_name = each_result['detail']['alarmName']
                alarm_reasondata_json = json.loads(each_result['detail']['state']['reasonData'])
                alarm_time = alarm_reasondata_json['startDate']
                alarm_threshold = alarm_reasondata_json['threshold']
                alarm_threshold_breach_value= str(alarm_reasondata_json['recentDatapoints'][0])
                final_data.append([instance_name,instance_id,metric_name,alarm_name,alarm_time,alarm_threshold,alarm_threshold_breach_value])

        # The final data is written to excel file
        final_df = pd.DataFrame(final_data,columns=['Instance Name','Instance Id','Metric Name','Alarm Name',"Alarm Time","Threshold",'Threshold Breach'])
        TMP_FILE_NAME = '/tmp/'+ "cloudwatch_Alarm_24hr_"+ str(getCurrentMilsec)+".csv"
        final_df.to_csv(TMP_FILE_NAME, index = False)
        s3_client.upload_file(Filename=TMP_FILE_NAME, Bucket='demobucket', Key="cloudwatch_Alarm_24hr/cloudwatch_Alarm_24hr_"+ str(getCurrentMilsec)+".csv")
        # The below code snippet is to send email. It uses Amazon SES service.
        SENDER = "test@gmail.com"
        RECIPIENTS = ["test2@gmail.com"]
        AWS_REGION = "us-west-2"
        SUBJECT = "Cloudwatch Alarm Monitoring mail for last 24hr data"
        BODY_TEXT = "Cloudwatch Alarm Monitoring mail for last 24hr data is attached with this mail for reference."
        ses_client = boto3.client('ses',region_name=AWS_REGION)
        msg = MIMEMultipart()
        msg['Subject'] = SUBJECT 
        msg['From'] = SENDER 
        msg['To'] = ",".join(RECIPIENTS)
        textpart = MIMEText(BODY_TEXT)
        msg.attach(textpart)
        att = MIMEApplication(open(TMP_FILE_NAME, 'rb').read())
        att.add_header('Content-Disposition','attachment',filename="cloudwatch_Alarm_24hr_"+ str(getCurrentMilsec)+".csv")
        msg.attach(att)
        response = ses_client.send_raw_email(
            Source=SENDER,
            Destinations=RECIPIENTS,
            RawMessage={ 'Data':msg.as_string() }
        )

    except Exception as e:
        print("Something went wrong, please investigate")
        traceback.print_exc()
        return {
            'StatusCode': 400,
            'Message': 'Something went wrong, Please Investigate. Error --> '+ str(e)
        }