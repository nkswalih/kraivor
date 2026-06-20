resource "aws_sqs_queue" "notification_queue" {
  name                        = "kraivor-notifications-${var.environment}"
  delay_seconds               = 0
  max_message_size            = 262144
  message_retention_seconds   = 86400
  receive_wait_time_seconds   = 10
  visibility_timeout_seconds  = 60

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.notification_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "notification_dlq" {
  name                      = "kraivor-notifications-dlq-${var.environment}"
  message_retention_seconds  = 1209600
}

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.notification_queue.arn
  function_name    = var.lambda_function_arn
  batch_size       = 1
}
