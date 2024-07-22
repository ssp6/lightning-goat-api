provider "aws" {
  region = "eu-west-2"  # Replace with your desired AWS region
}

resource "aws_s3_bucket" "my_bucket" {
  bucket = "lightning-goat"  # Replace with your preferred bucket name

  # Enable versioning
  versioning {
    enabled = true
  }

  # Enable server-side encryption
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "my_bucket_cors" {
  bucket = aws_s3_bucket.my_bucket.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

resource "aws_iam_user" "my_user" {
  name = "lightning-goat-user"
}

resource "aws_iam_access_key" "my_user_access_key" {
  user = aws_iam_user.my_user.name

  # Forces the creation of a new access key pair
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_iam_user_policy" "my_user_policy" {
  name = "lightning-goat-policy"
  user = aws_iam_user.my_user.name

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Action    = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject"
        ],
        Resource  = [
          aws_s3_bucket.my_bucket.arn,
          "${aws_s3_bucket.my_bucket.arn}/*"  # Include all objects in the bucket
        ]
      }
    ]
  })
}

output "access_key_id" {
  value = aws_iam_access_key.my_user_access_key.id
}

output "secret_access_key" {
  value     = aws_iam_access_key.my_user_access_key.secret
  sensitive = true
}
