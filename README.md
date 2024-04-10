## Automated CloudWatch alarm reporting system

The purpose of this code is to generate a report containing details of all Amazon CloudWatch alarms triggered in a specific AWS region within the last 24 hours. The report will be generated automatically by an AWS Lambda function, triggered by an Amazon EventBridge rule every 24 hours. The report will be in CSV format and will include columns such as instance name, instance ID, metric name, alarm name, alarm time, threshold value, and threshold breach value for each triggered alarm. The generated CSV file will be stored in an S3 bucket, and an email with the CSV file attached will be sent using Amazon SES.

![Cloudwatch_alarm_observability_last24hour_V02](https://github.com/aws-samples/automated-cloudwatch-alarm-reporting-system/assets/33568504/80e2e8f9-3201-4868-8ba6-95b093bb81b7)

## Automated Daily EC2 Instance Monitoring and Reporting

The purpose of this code is to generate a report containing dmonitoring data from of all the EC2 instances, including CPU utilization, memory usage, and disk usage from Amazon CloudWatch agents.This includes the process where an AWS Lambda function is triggered daily by an Amazon EventBridge rule to gather monitoring data of all the EC2 instances collected by cloudwatch agents which is sent to Amazon CloudWatch. This data is then compiled into a CSV file, stored in an S3 bucket, and sent as an email attachment using Amazon SES, effectively automating the daily monitoring and reporting process for all EC2 instances.
![Automated Daily EC2 Instance Monitoring and Reporting](https://github.com/aws-samples/automated-cloudwatch-alarm-reporting-system/assets/33568504/d0dd0278-231e-471b-828a-eb6aa39bbb38)



## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

