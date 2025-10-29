# ZAI Integration Guide for Nekro Agent

This guide explains how to deploy, start, and use the ZAI (Z.AI) integration with Nekro Agent.

## Overview

The ZAI integration allows Nekro Agent to use Z.AI's language models (like glm-4.5v and 0727-360B-API) as an alternative to OpenAI models. This integration provides:

- **Multiple Model Support**: Access to ZAI's advanced models including GLM and other specialized models
- **Streaming Support**: Real-time response streaming for better user experience  
- **Thinking Mode**: Optional chain-of-thought reasoning for more detailed responses
- **Configuration Management**: Easy switching between OpenAI and ZAI providers

## Installation & Setup

### 1. Dependencies

The ZAI SDK has been integrated directly into the Nekro Agent codebase. The following dependencies are required:

```bash
pip install requests pydantic aiofiles
```

### 2. File Structure

The integration includes the following new files:

```
nekro_agent/
├── services/agent/zai.py           # ZAI provider implementation
├── core/config.py                  # Updated with ZAI provider support
├── zai_sdk/                        # ZAI Python SDK
│   ├── __init__.py
│   ├── client.py
│   ├── models.py
│   ├── core/
│   ├── operations/
│   └── utils/
└── test_zai_simple.py              # Test script for ZAI functionality
```

## Configuration

### 1. Model Groups Configuration

The Nekro Agent configuration now supports a `PROVIDER` field in model groups:

```yaml
MODEL_GROUPS:
  zai:
    GROUP_NAME: "ZAI Models"
    CHAT_MODEL: "glm-4.5v"  # or "0727-360B-API"
    CHAT_PROXY: ""
    BASE_URL: "https://chat.z.ai"
    API_KEY: ""  # Leave empty to use auto-auth
    PROVIDER: "zai"  # NEW: Specifies the provider type
    MODEL_TYPE: "chat"
    ENABLE_VISION: true
    ENABLE_COT: true  # Enables thinking mode
```

### 2. Available ZAI Models

- **glm-4.5v**: Advanced visual understanding and analysis model
- **0727-360B-API**: Most advanced model, proficient in coding and tool use

### 3. Authentication

The ZAI integration supports two authentication modes:

1. **Auto-Authentication (Recommended)**: Leave `API_KEY` empty to use guest tokens
2. **API Key Authentication**: Provide your ZAI API key if you have one

### 4. Switching to ZAI

To use ZAI as your default provider, update the configuration:

```yaml
USE_MODEL_GROUP: "zai"  # Use the ZAI model group
```

## Usage Examples

### 1. Basic Chat Configuration

```yaml
# Example configuration for ZAI integration
MODEL_GROUPS:
  default:
    GROUP_NAME: "OpenAI Default"
    CHAT_MODEL: "gpt-4"
    BASE_URL: "https://api.openai.com/v1"
    API_KEY: "your-openai-key"
    PROVIDER: "openai"
    MODEL_TYPE: "chat"
    ENABLE_VISION: true
    ENABLE_COT: false
    
  zai-basic:
    GROUP_NAME: "ZAI Basic"
    CHAT_MODEL: "glm-4.5v"
    BASE_URL: "https://chat.z.ai"
    API_KEY: ""
    PROVIDER: "zai"
    MODEL_TYPE: "chat"
    ENABLE_VISION: true
    ENABLE_COT: false
    
  zai-advanced:
    GROUP_NAME: "ZAI Advanced with Thinking"
    CHAT_MODEL: "0727-360B-API"
    BASE_URL: "https://chat.z.ai"
    API_KEY: ""
    PROVIDER: "zai"
    MODEL_TYPE: "chat"
    ENABLE_VISION: true
    ENABLE_COT: true  # Enable chain-of-thought reasoning

USE_MODEL_GROUP: "zai-basic"  # Default to ZAI basic model
```

### 2. Dynamic Model Switching

You can switch between models by changing the `USE_MODEL_GROUP` setting without restarting:

```bash
# Switch to ZAI advanced model with thinking
USE_MODEL_GROUP: "zai-advanced"

# Switch back to OpenAI
USE_MODEL_GROUP: "default"
```

## Deployment

### 1. Docker Deployment

Follow the standard Nekro Agent Docker deployment process:

```bash
# Set up data directory
export NEKRO_DATA_DIR=/path/to/nekro-agent-data

# Copy and configure environment
cp docker/.env.example $NEKRO_DATA_DIR/.env

# Edit configuration to include ZAI settings
# Add ZAI model groups to your config files

# Start services
cd $NEKRO_DATA_DIR
docker compose --env-file .env up -d
```

### 2. Configuration Update

After deployment, update your model configuration through the web UI or by editing the configuration files directly.

## Testing the Integration

### 1. Basic Test

Use the provided test script to verify the integration:

```bash
python test_zai_simple.py
```

### 2. Web Interface Testing

1. Access the Nekro Agent web interface
2. Go to Configuration → Model Groups
3. Select the ZAI model group
4. Send a test message to verify functionality

### 3. Chat Platform Testing

Send messages through your configured chat platforms (Discord, QQ, etc.) to test the ZAI integration in real scenarios.

## Advanced Features

### 1. Thinking Mode (Chain of Thought)

When `ENABLE_COT: true` is set, ZAI models will provide detailed reasoning:

```yaml
zai-thinking:
  CHAT_MODEL: "0727-360B-API"
  PROVIDER: "zai"
  ENABLE_COT: true  # Enables detailed reasoning output
```

### 2. Streaming Responses

ZAI supports real-time streaming responses for better user experience:

```yaml
# In core configuration
AI_REQUEST_STREAM_MODE: true  # Enable streaming for all providers
```

### 3. Model-Specific Parameters

Fine-tune model behavior with custom parameters:

- `temperature`: Controls randomness (0.0-2.0)
- `top_p`: Controls diversity (0.0-1.0)
- `max_tokens`: Maximum response length

## Troubleshooting

### 1. Authentication Issues

If you see "Missing signature header" errors:
- Ensure `API_KEY` is empty for auto-authentication
- Check that `BASE_URL` is set to `https://chat.z.ai`

### 2. Model Not Found

If you see model-related errors:
- Verify the model name is correct (`glm-4.5v` or `0727-360B-API`)
- Check that the ZAI service is accessible

### 3. Streaming Issues

If streaming doesn't work:
- Ensure `AI_REQUEST_STREAM_MODE: true` in configuration
- Check network connectivity to ZAI services

### 4. Performance Optimization

For better performance:
- Use appropriate `max_tokens` settings
- Set reasonable timeout values
- Consider using the lighter `glm-4.5v` model for simple tasks

## API Compatibility

The ZAI integration maintains compatibility with the existing Nekro Agent architecture:

- **Response Format**: Both OpenAI and ZAI providers return compatible response objects
- **Error Handling**: Consistent error handling across providers
- **Logging**: Unified logging format for all providers
- **Metrics**: Token consumption and performance metrics

## Best Practices

1. **Model Selection**: Use `glm-4.5v` for general tasks, `0727-360B-API` for complex reasoning
2. **Authentication**: Use auto-authentication unless you have specific API key requirements
3. **Streaming**: Enable streaming for better user experience in chat interfaces
4. **Thinking Mode**: Enable CoT for complex problem-solving tasks
5. **Fallback**: Configure both OpenAI and ZAI models for reliability

## Support

For issues related to:
- **Nekro Agent Integration**: Check the main Nekro Agent documentation and issues
- **ZAI API**: Refer to Z.AI documentation or support channels
- **Configuration**: Review the configuration examples in this guide

---

This integration brings the power of Z.AI's advanced language models to the Nekro Agent ecosystem, providing users with more choice and flexibility in their AI interactions.