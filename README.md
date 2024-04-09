## Automated CloudWatch alarm reporting system

The purpose of this code is to generate a report containing details of all CloudWatch alarms triggered in a specific AWS region within the last 24 hours. The report will be generated automatically by an AWS Lambda function, triggered by an Amazon EventBridge rule every 24 hours. The report will be in CSV format and will include columns such as instance name, instance ID, metric name, alarm name, alarm time, threshold value, and threshold breach value for each triggered alarm. The generated CSV file will be stored in an S3 bucket, and an email with the CSV file attached will be sent using Amazon SES.
![Cloudwatch_alarm_observability_last24hour_V02](https://github.com/aws-samples/automated-cloudwatch-alarm-reporting-system/assets/33568504/80e2e8f9-3201-4868-8ba6-95b093bb81b7)


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

