resource "aws_s3_bucket" "reports" {
  bucket = "kraivor-reports-${var.environment}"
}

resource "aws_s3_bucket_lifecycle_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id

  rule {
    id     = "transition-to-glacier"
    status = "Enabled"

    transition {
      days          = 730
      storage_class = "GLACIER"
    }

    expiration {
      days = 1825
    }
  }
}

resource "aws_s3_bucket" "archives" {
  bucket = "kraivor-archives-${var.environment}"
}

resource "aws_s3_bucket" "exports" {
  bucket = "kraivor-exports-${var.environment}"
}

variable "environment" {}
