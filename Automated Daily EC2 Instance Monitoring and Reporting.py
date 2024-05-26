import boto3, json
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
        region_name = 'us-west-2'  # update the region where you run this code
        s3_bucket_name = 'testbucket'  # update the s3 bucket name to upload the generated csv file
        s3_conf_file = 'CPU_mem_disk_conf_json.json'  # update the configuration file name
        SENDER = "test@gmail.com"  # update the verified sender nad recipients email address from AWS SES service
        RECIPIENTS = ["test@gmail.com"]
        final_data = []
        cloudwatch_client = boto3.client('cloudwatch', region_name=region_name)
        s3_client = boto3.client('s3', region_name=region_name)
        ses_client = boto3.client('ses', region_name=region_name)
        SUBJECT = "EC2 instances Cloudwatch Metric Monitoring mail for last 24hr data"
        BODY_TEXT = "EC2 instances Cloudwatch Metric Monitoring mail for last 24hr data is attached with this mail for reference."

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
        metric_statistics_lookup_instances = json.loads(filedata)
        # the below code gets the required cloudwatch metrics statistics (cpu utilization, memory utilization, root and ebs disk usage space) from the cloudwatch.
        ebs_max_count = 0
        for each_ec2Instance in metric_statistics_lookup_instances:
            instance_name = each_ec2Instance['instance_name']
            instance_id = each_ec2Instance['instance_id']
            metrics = each_ec2Instance['metrics']
            each_data = []
            each_data.append(instance_name)
            each_data.append(instance_id)
            if each_ec2Instance['ebs_disk_count'] > ebs_max_count:
                ebs_max_count = each_ec2Instance['ebs_disk_count']

            for each_metric in metrics:
                namespace = each_metric['nameSpace']
                metricName = each_metric['metricName']
                dimensions = each_metric['dimensions']

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
                sorted_by_maximum_value = sorted(each_ec2Instance_stats["Datapoints"], key=itemgetter('Maximum'),
                                                 reverse=True)
                if metricName == "CPUUtilization":
                    each_data.append(round(sorted_by_maximum_value[0]['Average'], 2))
                    each_data.append(round(sorted_by_maximum_value[0]['Maximum'], 2))

                elif metricName == "mem_used_percent":
                    each_data.append(round(sorted_by_maximum_value[0]['Average'], 2))
                    each_data.append(round(sorted_by_maximum_value[0]['Maximum'], 2))

                elif metricName == "disk_used":
                    if dimensions[-1]['Value'] == '/':
                        each_data.append(round((sorted_by_maximum_value[0]['Maximum'] / (1024 ** 3)), 2))
                    elif '/mnt/' in dimensions[-1]['Value']:
                        each_data.append(round((sorted_by_maximum_value[0]['Maximum'] / (1024 ** 3)), 2))
                elif metricName == "disk_total":
                    if dimensions[-1]['Value'] == '/':
                        each_data.append(round((sorted_by_maximum_value[0]['Maximum'] / (1024 ** 3)), 2))
                    elif '/mnt/' in dimensions[-1]['Value']:
                        each_data.append(round((sorted_by_maximum_value[0]['Maximum'] / (1024 ** 3)), 2))
                elif metricName == "disk_free":
                    if dimensions[-1]['Value'] == '/':
                        each_data.append(round((sorted_by_maximum_value[0]['Maximum'] / (1024 ** 3)), 2))
                    elif '/mnt/' in dimensions[-1]['Value']:
                        each_data.append(round((sorted_by_maximum_value[0]['Maximum'] / (1024 ** 3)), 2))
            final_data.append(each_data)

        # The final data is written to CSV file

        default_column_names = ['Instance Name', 'Instance Id', 'Average CPU utilization Percent',
                                'Max CPU utilization Percent',
                                'Average Memory utilization Percent', 'Max Memory utilization Percent',
                                'Root disk total in GB',
                                'Root disk used in GB', 'Root disk free in GB']
        if ebs_max_count > 0:
            ebs_column_names = []
            for ebs_num in range(0, ebs_max_count):
                ebs_column_names.append('EBS' + str(ebs_num) + ' disk total  in GB')
                ebs_column_names.append('EBS' + str(ebs_num) + ' disk used  in GB')
                ebs_column_names.append('EBS' + str(ebs_num) + ' disk free in GB')
            column_names = default_column_names + ebs_column_names

        else:
            column_names = default_column_names

        final_df = pd.DataFrame(final_data,
                                columns=column_names)
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
            'Message': 'Something went wrong, Please Investigate. Error --> ' + str(e)
        }

