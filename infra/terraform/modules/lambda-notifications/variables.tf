variable "environment" {
  description = "Environment name (dev / prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "ses_from_email" {
  description = "Sender email address for SES"
  type        = string
  default     = "noreply@kraivor.com"
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications"
  type        = string
  default     = ""
}
