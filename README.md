# Lightning Goat — API

This was a little project to learn more about video streaming and how to use Socket.io.

I applied for a contract position that I didn't quite have the experience for, and it bothered me that I wasn't quite sure how to build what they were looking for.

So I spent a couple of days learning and figuring out how it could be done.

The code's messy and not well documented, but it gets the job done and I have a much better idea of how to build this now.


## What it does

It's fairly simple:
- Authenticated using Clerk
- Upload an mp4 file to S3
- That file is streamed back to you frame by frame through websockets (using SocketIO)
- Log when a user draws on a video, with which frame they have drawn on

## How to run
```
// Create S3 bucket using terraform
cd terraform
terraform init
terraform plan
terraform apply

// Set .env variables from .env.example
make install
make run

```
