data "archive_file" "lambda_code" {
  type        = "zip"
  source_dir  = "${path.module}/../../../lambda/notifications"
  output_path = "${path.module}/lambda-notifications.zip"
}

resource "aws_iam_role" "lambda_role" {
  name = "kraivor-notifications-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "kraivor-notifications-${var.environment}"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish",
        ]
        Resource = "*"
      },
    ]
  })
}

resource "aws_lambda_function" "notifications" {
  filename         = data.archive_file.lambda_code.output_path
  function_name    = "kraivor-notifications-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "main.handler"
  runtime          = "python3.11"
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      AWS_REGION    = var.aws_region
      SES_FROM_EMAIL = var.ses_from_email
      SLACK_WEBHOOK_URL = var.slack_webhook_url
    }
  }
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/kraivor-notifications-${var.environment}"
  retention_in_days = 14
}
