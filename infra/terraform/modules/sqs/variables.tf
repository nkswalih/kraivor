variable "environment" {
  description = "Environment name (dev / prod)"
  type        = string
}

variable "lambda_function_arn" {
  description = "ARN of the Lambda function to trigger"
  type        = string
}
