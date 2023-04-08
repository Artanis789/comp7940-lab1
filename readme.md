# The link of the chatbot:
- http://t.me/minghebot
# How to run the service locally?
## Prerequisites:
### 1. Docker on your computer or VM
### 2. docker-compose on your computer or VM
### 2. A telegram chatbot token
### 3. An OpenAI API key

## How to RUN?
### 1. Edit docker-compose.yaml
- Replace ACCESS_TOKEN with your own telegram token
- Replace OPENAI_API_KEY with your own OpenAI API key
### 2. Run this command
```bash
docker-compose up -d
```

## How to check logs?
```bash
docker logs -f [NAME OF YOUR CHATBOT CONTAINER]
```

## How to shut down the service?
```bash
docker-compose down
```