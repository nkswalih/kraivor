output "queue_url" {
  description = "URL of the notification SQS queue"
  value       = aws_sqs_queue.notification_queue.url
}

output "queue_arn" {
  description = "ARN of the notification SQS queue"
  value       = aws_sqs_queue.notification_queue.arn
}

output "dlq_arn" {
  description = "ARN of the dead-letter queue"
  value       = aws_sqs_queue.notification_dlq.arn
}
