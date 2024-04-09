import boto3,json
from datetime import datetime
import pytz
from operator import itemgetter
import traceback
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

def lambda_handler(event, context):
    try:
        time_millisec = 86400000  # 24 hrs in millisec
        region_name='us-west-2'  # update the region where you run this code
        s3_bucket_name = 'demobucket' # update the s3 bucket name to upload the generated csv file
        s3_conf_file = 'CPU_mem_disk_conf_json.json' # update the configuration file name
        SENDER = "test@gmail.com"  # update the verified sender nad recipients email address from AWS SES service
        RECIPIENTS = ["test01@gmail.com"]
        final_data = []
        cloudwatch_client = boto3.client('cloudwatch', region_name=region_name)
        s3_client = boto3.client('s3', region_name=region_name)
        ses_client = boto3.client('ses', region_name=region_name)
        SUBJECT = "Cloudwatch Metric Monitoring mail for last 24hr data"
        BODY_TEXT = "Cloudwatch Metric Monitoring mail for last 24hr data is attached with this mail for reference."
        # below function is to convert the date time to millisecond
        def convertToMil(value):
            dt_obj = datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S')
            result = int(dt_obj.timestamp() * 1000)
            return result
        currentdateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        getCurrentMilsec = convertToMil(str(currentdateTime))
        getYesterdayMilsec = getCurrentMilsec - time_millisec
        s3_fileobj = s3_client.get_object(Bucket=s3_bucket_name, Key=s3_conf_file)
        filedata = s3_fileobj['Body'].read().decode('utf-8')
        metric_statistics_lookup_instances=json.loads(filedata)
        # the below code gets the required cloudwatch metrics statistics (cpu utilization, memory utilization, root and ebs disk usage space) from the cloudwatch.
        for each_ec2Instance in metric_statistics_lookup_instances:
            instance_name = each_ec2Instance['instance_name']
            instance_id = each_ec2Instance['instance_id']
            metrics = each_ec2Instance['metrics']
            cpu_utilization_json = {}
            mem_utilization_json = {}
            root_disk_used_json = {}
            root_disk_total_json = {}
            root_disk_free_json = {}
            ebs1_disk_used_json = {}
            ebs1_disk_total_json = {}
            ebs1_disk_free_json = {}
            ebs2_disk_used_json = {}
            ebs2_disk_total_json = {}
            ebs2_disk_free_json = {}
            for each_metric in metrics:
                namespace = each_metric['nameSpace']
                metricName = each_metric['metricName']
                dimensions = each_metric['dimensions']
                dimensions.append({'Name': 'InstanceId','Value':instance_id})
                statistics = each_metric['statistics']
                unit = each_metric['unit']
                each_ec2Instance_stats = cloudwatch_client.get_metric_statistics(
                    Namespace=namespace,
                    MetricName=metricName,
                    Dimensions=dimensions,
                    StartTime=datetime.fromtimestamp(getYesterdayMilsec / 1000.0, tz=pytz.timezone('Asia/Kolkata')),
                    EndTime=datetime.fromtimestamp(getCurrentMilsec / 1000.0, tz=pytz.timezone('Asia/Kolkata')),
                    Period=300,
                    Statistics=statistics,
                    Unit=unit
                )
                sorted_by_maximum_value = sorted(each_ec2Instance_stats["Datapoints"], key=itemgetter('Maximum'), reverse=True)

                if metricName == "CPUUtilization":
                    cpu_utilization_json = sorted_by_maximum_value[0]
                elif metricName == "mem_used_percent":
                    mem_utilization_json = sorted_by_maximum_value[0]
                elif metricName == "disk_used":
                    if dimensions[2]['Value']=='/':
                        root_disk_used_json = sorted_by_maximum_value[0]
                    elif dimensions[2]['Value']=='/mnt/ebs_volume1':
                        ebs1_disk_used_json = sorted_by_maximum_value[0]
                    elif dimensions[2]['Value'] == '/mnt/ebs_volume2':
                        ebs2_disk_used_json = sorted_by_maximum_value[0]
                elif metricName == "disk_total":
                    if dimensions[2]['Value']=='/':
                        root_disk_total_json = sorted_by_maximum_value[0]
                    elif dimensions[2]['Value']=='/mnt/ebs_volume1':
                        ebs1_disk_total_json = sorted_by_maximum_value[0]
                    elif dimensions[2]['Value'] == '/mnt/ebs_volume2':
                        ebs2_disk_total_json = sorted_by_maximum_value[0]
                elif metricName == "disk_free":
                    if dimensions[2]['Value']=='/':
                        root_disk_free_json = sorted_by_maximum_value[0]
                    elif dimensions[2]['Value']=='/mnt/ebs_volume1':
                        ebs1_disk_free_json = sorted_by_maximum_value[0]
                    elif dimensions[2]['Value'] == '/mnt/ebs_volume2':
                        ebs2_disk_free_json = sorted_by_maximum_value[0]

            each_data=[]
            each_data.append(instance_name)
            each_data.append(instance_id)
            each_data.append(round(cpu_utilization_json['Average'],2))
            each_data.append(round(cpu_utilization_json['Maximum'],2))
            each_data.append(round(mem_utilization_json['Average'],2))
            each_data.append(round(mem_utilization_json['Maximum'],2))
            if len(root_disk_total_json) > 0:
                each_data.append(round((root_disk_total_json['Maximum']/ (1024**3)),2))
                each_data.append(round((root_disk_used_json['Maximum']/ (1024**3)),2))
                each_data.append(round((root_disk_free_json['Maximum']/ (1024**3)),2))
            if len(ebs1_disk_total_json)>0:
                each_data.append(round((ebs1_disk_total_json['Maximum']/ (1024**3)),2))
                each_data.append(round((ebs1_disk_used_json['Maximum']/ (1024**3)),2))
                each_data.append(round((ebs1_disk_free_json['Maximum']/ (1024**3)),2))
            if len(ebs2_disk_total_json)>0:
                each_data.append(round((ebs2_disk_total_json['Maximum']/ (1024**3)),2))
                each_data.append(round((ebs2_disk_used_json['Maximum']/ (1024**3)),2))
                each_data.append(round((ebs2_disk_free_json['Maximum']/ (1024**3)),2))

            final_data.append(each_data)
        # The final data is written to excel file
        final_df = pd.DataFrame(final_data,
                                columns=['Instance Name', 'Instance Id', 'Average CPU utilization Percent', 'Max CPU utilization Percent',
                                         'Average Memory utilization Percent', 'Max Memory utilization Percent','Root disk total in GB',
                                         'Root disk used in GB','Root disk free in GB','EBS1 disk total in GB','EBS1 disk used in GB',
                                         'EBS1 disk free in GB','EBS2 disk total in GB','EBS2 disk used in GB','EBS2 disk free in GB'])
        TMP_FILE_NAME = '/tmp/' + "cpu_mem_disk_usage_24hr_" + str(getCurrentMilsec) + ".csv"
        final_df.to_csv(TMP_FILE_NAME, index=False)
        s3_client.upload_file(Filename=TMP_FILE_NAME, Bucket=s3_bucket_name,
                              Key="cpu_mem_disk_usage_24hr/cpu_mem_disk_usage_24hr_" + str(getCurrentMilsec) + ".csv")
        # The below code snippet is to send email. It uses Amazon SES service.
        msg = MIMEMultipart()
        msg['Subject'] = SUBJECT
        msg['From'] = SENDER
        msg['To'] = ",".join(RECIPIENTS)
        textpart = MIMEText(BODY_TEXT)
        msg.attach(textpart)
        att = MIMEApplication(open(TMP_FILE_NAME, 'rb').read())
        att.add_header('Content-Disposition', 'attachment',
                       filename="cpu_mem_disk_usage_24hr_" + str(getCurrentMilsec) + ".csv")
        msg.attach(att)
        response = ses_client.send_raw_email(
            Source=SENDER,
            Destinations=RECIPIENTS,
            RawMessage={'Data': msg.as_string()}
        )
    except Exception as e:
            print("Something went wrong, please investigate")
            traceback.print_exc()
            return {
                'StatusCode': 400,
                'Message': 'Something went wrong, Please Investigate. Error --> '+ str(e)
            }

