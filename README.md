# Voice Agent Function Calling Python Demo

This repository serves as a reference implementation for integrating function calling capabilities with Deepgram's Voice Agent API using Python Flask. It demonstrates production-ready patterns for building AI Voice Agent applications with clientside function calling. In addition, it surfaces logs to the user to help understand the flow from user to assistant to LLM.

## UI
![image](https://github.com/user-attachments/assets/30d5bfc3-4686-4f5a-a49b-9d38a6f85d0b)




## Sign-up to Deepgram

Before you start, it's essential to generate a Deepgram API key to use in this project. [Sign-up now for Deepgram](https://console.deepgram.com/signup).

## Quickstart

This reference implementation demonstrates:

- Core function calling patterns with Voice Agent API
- Using Python Flask to build a simple web application
- Natural conversation flow using agent filler messages
- Customer information lookup and verification
- Order history retrieval
- Appointment scheduling and management
- Graceful conversation termination through an `end_call` function
- Logging in the UI for debugging

### Function Calling Architecture
The implementation uses a three-layer architecture:
- Function definitions that guide the LLM's behavior
- Function handlers that route requests
- Business logic that executes the actual functionality

### Natural Conversation Flow
Shows how to implement natural dialogue patterns:
- Agent filler messages for lookup operations
- Proper message sequencing
- Audio completion handling
- Clean session termination

## Project Structure

```
├── common/
│   ├── agent_functions.py    # Function definitions and routing
│   ├── business_logic.py     # Core function implementations
│   ├── config.py             # Configuration settings
│   ├── log_formatter.py      # Logger setup
├── client.py             # WebSocket client and message handling
```

## Mock Data System

The implementation uses a mock data system for demonstration:
- Generates realistic customer, order, and appointment data
- Saves data to timestamped JSON files in `mock_data_outputs/`
- Configurable through `config.py`

### Artificial Delays
The implementation demonstrates how to handle real-world latency:
- Configurable database operation delays in `config.py`
- Helps simulate production environment timing

## Setup Instructions

0. Make sure you have portaudio installed.

In macOS:
```bash
brew install portaudio:
```

In Ubuntu:
```bash
sudo apt-get install portaudio19-dev
```

`pipenv` can be used to manage virtual env. and packages in one easy to use tool. Instead of running pip commands, you just use [pipenv](https://pypi.org/project/pipenv/).

1. Install pipenv if not already installed.

```bash
pip install pipenv
```

2. Switch to the pipenv virtual environment:

```bash
pipenv shell
```

3. Install the project dependencies:

In the root directory of the project, run the following command to install the dependencies:

```bash
pipenv install -r requirements.txt
```

4. Set your Deepgram API key. Either programatically:
```bash
export DEEPGRAM_API_KEY=<your-key-here>
```
   - or in a file named `.env` within your root directory which has this entry:
```
DEEPGRAM_API_KEY=<your-key-here>
```

## Application Usage

1. Run the client:
   ```bash
   python client.py
   ```

> The application will be available at http://localhost:5000

2. Use headphones to prevent audio feedback (the agent hearing itself).

## Example Interactions

The voice agent handles natural conversations like:

```
User: "I need to check my order status"
Agent: "Let me look that up for you..."
[Agent executes customer lookup]
Agent: "I can see you have two recent orders. Your most recent
       order from last week is currently being shipped..."
```

## Configuration

Key settings in `config.py`:
- `ARTIFICIAL_DELAY`: Configurable delays for database operations
- `MOCK_DATA_SIZE`: Control size of generated test data

## Deploy to Fly.io

1. **Install the Fly CLI** (if needed): [fly.io/docs/hands-on/install-flyctl](https://fly.io/docs/hands-on/install-flyctl)

2. **Log in** (from the project root):
   ```bash
   fly auth login
   ```

3. **Set your Deepgram API key as a secret** (required for TTS/voice agent):
   ```bash
   fly secrets set DEEPGRAM_API_KEY=your-deepgram-api-key-here
   ```

4. **Deploy**:
   ```bash
   fly deploy
   ```
   On first deploy, Fly creates the app from `fly.toml` if it doesn’t exist yet.

5. **Open the app**:
   ```bash
   fly open
   ```

- App name and region are in `fly.toml` (`app = 'deepgram-agent-demo'`, `primary_region = 'sjc'`). Change them if you prefer.
- To view logs: `fly logs`
- To scale or change VM size: adjust `[[vm]]` in `fly.toml` and redeploy.

## Issue Reporting

If you have found a bug or if you have a feature request, please report them at this repository issues section. Please do not report security vulnerabilities on the public GitHub issue tracker. The [Security Policy](./SECURITY.md) details the procedure for contacting Deepgram.

## Author

[Deepgram](https://deepgram.com)

## License

This project is licensed under the MIT license. See the [LICENSE](./LICENSE) file for more info.
