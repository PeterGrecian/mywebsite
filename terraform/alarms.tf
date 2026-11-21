# Cost guard for the mywebsite Lambda (STATE Pending "Cost alarm", 2026-11-21).
#
# Baseline, 14 days to 2026-11-21: per hour, invocations median 108, p99 262,
# max 1,163; Duration sum median 17 s, p99 50 s, max 211 s. The function has
# 512 MB and reserved concurrency 20, so the true worst case is 20 x 0.5 GB
# running flat out: 36,000 GB-s an hour, about $0.60/h. These alarms fire
# long before that, and well before the 400,000 GB-s/month free tier.
#
# Both notify NotifyMe, the same SNS topic as the account-wide
# LambdaRunawayInvocations alarm; it is subscribed to the `alerting` Lambda.
# Two alarms keep the account inside CloudWatch's 10 free alarms.

data "aws_sns_topic" "notify_me" {
  name = "NotifyMe"
}

resource "aws_cloudwatch_metric_alarm" "mywebsite_hourly_invocations" {
  alarm_name          = "mywebsite-hourly-invocations"
  alarm_description   = "mywebsite Lambda: over 3,000 invocations in an hour (normal ~100, max seen 1,163). A crawler storm or a loop; check the access log."
  namespace           = "AWS/Lambda"
  metric_name         = "Invocations"
  dimensions          = { FunctionName = aws_lambda_function.mywebsite.function_name }
  statistic           = "Sum"
  period              = 3600
  evaluation_periods  = 1
  threshold           = 3000
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [data.aws_sns_topic.notify_me.arn]
  ok_actions          = [data.aws_sns_topic.notify_me.arn]
}

resource "aws_cloudwatch_metric_alarm" "mywebsite_hourly_compute" {
  alarm_name          = "mywebsite-hourly-compute"
  alarm_description   = "mywebsite Lambda: over 600 s of compute in an hour (300 GB-s at 512 MB; normal ~17 s, max seen 211 s). Sustained, this would use half the monthly free tier."
  namespace           = "AWS/Lambda"
  metric_name         = "Duration"
  dimensions          = { FunctionName = aws_lambda_function.mywebsite.function_name }
  statistic           = "Sum"
  period              = 3600
  evaluation_periods  = 1
  threshold           = 600000
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [data.aws_sns_topic.notify_me.arn]
  ok_actions          = [data.aws_sns_topic.notify_me.arn]
}
