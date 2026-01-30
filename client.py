from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import pyaudio
import asyncio
import websockets
import os
import json
import threading
import janus
import queue
import sys
import time
import audioop
import requests
from datetime import datetime
from common.agent_functions import FUNCTION_MAP
from common.agent_templates import AgentTemplates, AGENT_AUDIO_SAMPLE_RATE
import logging
from common.business_logic import MOCK_DATA
from common.log_formatter import CustomFormatter


# Configure Flask and SocketIO
app = Flask(__name__, static_folder="./static", static_url_path="/")
socketio = SocketIO(app)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with the custom formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(CustomFormatter(socketio=socketio))
logger.addHandler(console_handler)

# Remove any existing handlers from the root logger to avoid duplicate messages
logging.getLogger().handlers = []


class VoiceAgent:
    def __init__(
        self,
        industry="deepgram",
        voiceModel="aura-2-thalia-en",
        voiceName="",
        language="en",
        browser_audio=False,
    ):
        self.mic_audio_queue = asyncio.Queue()
        self.speaker = None
        self.ws = None
        self.is_running = False
        self.loop = None
        self.audio = None
        self.stream = None
        self.input_device_id = None
        self.output_device_id = None
        self.browser_audio = browser_audio  # For browser microphone input
        self.browser_output = browser_audio  # Use same setting for browser output
        self.agent_templates = AgentTemplates(
            industry, voiceModel, voiceName, language=language
        )

    def set_loop(self, loop):
        self.loop = loop

    async def setup(self):
        dg_api_key = os.environ.get("DEEPGRAM_API_KEY")
        if dg_api_key is None:
            logger.error("DEEPGRAM_API_KEY env var not present")
            return False

        settings = self.agent_templates.settings

        try:
            self.ws = await websockets.connect(
                self.agent_templates.voice_agent_url,
                extra_headers={"Authorization": f"Token {dg_api_key}"},
            )
            await self.ws.send(json.dumps(settings))
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}")
            return False

    def audio_callback(self, input_data, frame_count, time_info, status_flag):
        if self.is_running and self.loop and not self.loop.is_closed():
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.mic_audio_queue.put(input_data), self.loop
                )
                future.result(timeout=1)  # Add timeout to prevent blocking
            except Exception as e:
                logger.error(f"Error in audio callback: {e}")
        return (input_data, pyaudio.paContinue)

    async def start_microphone(self):
        try:
            self.audio = pyaudio.PyAudio()

            # List available input devices
            info = self.audio.get_host_api_info_by_index(0)
            numdevices = info.get("deviceCount")
            logger.info(f"Number of devices: {numdevices}")
            logger.info(
                f"Selected input device index from frontend: {self.input_device_id}"
            )

            # Log all available input devices
            available_devices = []
            for i in range(0, numdevices):
                device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
                if device_info.get("maxInputChannels") > 0:
                    available_devices.append(i)

            # If a specific device index was provided from the frontend, use it
            if self.input_device_id and self.input_device_id.isdigit():
                requested_index = int(self.input_device_id)
                # Verify the requested index is valid
                if requested_index in available_devices:
                    input_device_index = requested_index
                    logger.info(f"Using selected device index: {input_device_index}")
                else:
                    logger.warning(
                        f"Requested device index {requested_index} not available, using default"
                    )

            # If still no device selected, use first available
            if input_device_index is None and available_devices:
                input_device_index = available_devices[0]
                logger.info(f"Using first available device index: {input_device_index}")

            if input_device_index is None:
                raise Exception("No input device found")

            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.agent_templates.user_audio_sample_rate,
                input=True,
                input_device_index=input_device_index,
                frames_per_buffer=self.agent_templates.user_audio_samples_per_chunk,
                stream_callback=self.audio_callback,
            )
            self.stream.start_stream()
            logger.info("Microphone started successfully")
            return self.stream, self.audio
        except Exception as e:
            logger.error(f"Error starting microphone: {e}")
            if self.audio:
                self.audio.terminate()
            raise

    def cleanup(self):
        """Clean up audio resources"""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error closing audio stream: {e}")

        if self.audio:
            try:
                self.audio.terminate()
            except Exception as e:
                logger.error(f"Error terminating audio: {e}")

    async def sender(self):
        try:
            # Log when sender starts
            logger.info(f"Audio sender started (browser_audio={self.browser_audio})")

            # Track if we've logged the first chunk
            first_chunk = True

            while self.is_running:
                data = await self.mic_audio_queue.get()
                if self.ws and data:
                    # Log the first audio chunk we send
                    if first_chunk:
                        logger.info(
                            f"Sending first audio chunk to Deepgram: {len(data)} bytes"
                        )
                        first_chunk = False

                    # Send the audio data to Deepgram
                    await self.ws.send(data)

        except Exception as e:
            logger.error(f"Error in sender: {e}")
            # Print stack trace for debugging
            import traceback

            logger.error(traceback.format_exc())

    async def receiver(self):
        try:
            self.speaker = Speaker(browser_output=self.browser_output)
            last_user_message = None
            last_function_response_time = None
            in_function_chain = False

            with self.speaker:
                async for message in self.ws:
                    if isinstance(message, str):
                        logger.info(f"Server: {message}")
                        message_json = json.loads(message)
                        message_type = message_json.get("type")
                        current_time = time.time()

                        if message_type == "UserStartedSpeaking":
                            self.speaker.stop()
                        elif message_type == "ConversationText":
                            # Emit the conversation text to the client
                            socketio.emit("conversation_update", message_json)

                            if message_json.get("role") == "user":
                                last_user_message = current_time
                                in_function_chain = False
                            elif message_json.get("role") == "assistant":
                                in_function_chain = False

                        elif message_type == "FunctionCalling":
                            if in_function_chain and last_function_response_time:
                                latency = current_time - last_function_response_time
                                logger.info(
                                    f"LLM Decision Latency (chain): {latency:.3f}s"
                                )
                            elif last_user_message:
                                latency = current_time - last_user_message
                                logger.info(
                                    f"LLM Decision Latency (initial): {latency:.3f}s"
                                )
                                in_function_chain = True

                        elif message_type == "FunctionCallRequest":
                            functions = message_json.get("functions", [])
                            if len(functions) > 1:
                                raise NotImplementedError(
                                    "Multiple functions not supported"
                                )
                            function_name = functions[0].get("name")
                            function_call_id = functions[0].get("id")
                            parameters = json.loads(functions[0].get("arguments", {}))

                            logger.info(f"Function call received: {function_name}")
                            logger.info(f"Parameters: {parameters}")

                            start_time = time.time()
                            try:
                                func = FUNCTION_MAP.get(function_name)
                                if not func:
                                    raise ValueError(
                                        f"Function {function_name} not found"
                                    )

                                # Special handling for functions that need websocket
                                if function_name in ["agent_filler", "end_call"]:
                                    result = await func(self.ws, parameters)

                                    if function_name == "agent_filler":
                                        # Extract messages
                                        inject_message = result["inject_message"]
                                        function_response = result["function_response"]

                                        # First send the function response
                                        response = {
                                            "type": "FunctionCallResponse",
                                            "id": function_call_id,
                                            "name": function_name,
                                            "content": json.dumps(function_response),
                                        }
                                        await self.ws.send(json.dumps(response))
                                        logger.info(
                                            f"Function response sent: {json.dumps(function_response)}"
                                        )

                                        # Update the last function response time
                                        last_function_response_time = time.time()
                                        # Then just inject the message and continue
                                        await inject_agent_message(
                                            self.ws, inject_message
                                        )
                                        continue

                                    elif function_name == "end_call":
                                        # Extract messages
                                        inject_message = result["inject_message"]
                                        function_response = result["function_response"]
                                        close_message = result["close_message"]

                                        # First send the function response
                                        response = {
                                            "type": "FunctionCallResponse",
                                            "id": function_call_id,
                                            "name": function_name,
                                            "content": json.dumps(function_response),
                                        }
                                        await self.ws.send(json.dumps(response))
                                        logger.info(
                                            f"Function response sent: {json.dumps(function_response)}"
                                        )

                                        # Update the last function response time
                                        last_function_response_time = time.time()

                                        # Then wait for farewell sequence to complete
                                        await wait_for_farewell_completion(
                                            self.ws, self.speaker, inject_message
                                        )

                                        # Finally send the close message and exit
                                        logger.info(f"Sending ws close message")
                                        await close_websocket_with_timeout(self.ws)
                                        self.is_running = False
                                        break
                                else:
                                    result = await func(parameters)

                                execution_time = time.time() - start_time
                                logger.info(
                                    f"Function Execution Latency: {execution_time:.3f}s"
                                )

                                # Send the response back
                                response = {
                                    "type": "FunctionCallResponse",
                                    "id": function_call_id,
                                    "name": function_name,
                                    "content": json.dumps(result),
                                }
                                await self.ws.send(json.dumps(response))
                                logger.info(
                                    f"Function response sent: {json.dumps(result)}"
                                )

                                # Update the last function response time
                                last_function_response_time = time.time()

                            except Exception as e:
                                logger.error(f"Error executing function: {str(e)}")
                                result = {"error": str(e)}
                                response = {
                                    "type": "FunctionCallResponse",
                                    "id": function_call_id,
                                    "name": function_name,
                                    "content": json.dumps(result),
                                }
                                await self.ws.send(json.dumps(response))

                        elif message_type == "Welcome":
                            logger.info(
                                f"Connected with session ID: {message_json.get('session_id')}"
                            )
                        elif message_type == "CloseConnection":
                            logger.info("Closing connection...")
                            await self.ws.close()
                            break

                    elif isinstance(message, bytes):
                        await self.speaker.play(message)

        except Exception as e:
            logger.error(f"Error in receiver: {e}")

    async def run(self):
        if not await self.setup():
            return

        self.is_running = True
        try:
            # Only start the microphone if not using browser audio
            if not self.browser_audio:
                stream, audio = await self.start_microphone()

            await asyncio.gather(
                self.sender(),
                self.receiver(),
            )
        except Exception as e:
            logger.error(f"Error in run: {e}")
        finally:
            self.is_running = False
            self.cleanup()
            if self.ws:
                await self.ws.close()


class Speaker:
    def __init__(self, agent_audio_sample_rate=None, browser_output=False):
        self._queue = None
        self._stream = None
        self._thread = None
        self._stop = None
        self.agent_audio_sample_rate = (
            agent_audio_sample_rate if agent_audio_sample_rate else 16000
        )
        self.browser_output = browser_output

    def __enter__(self):
        # Only initialize PyAudio for system audio output, not browser output
        if not self.browser_output:
            audio = pyaudio.PyAudio()
            self._stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.agent_audio_sample_rate,
                input=False,
                output=True,
            )
        else:
            self._stream = None

        self._queue = janus.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=_play,
            args=(self._queue, self._stream, self._stop, self.browser_output),
            daemon=True,
        )
        self._thread.start()

    def __exit__(self, exc_type, exc_value, traceback):
        self._stop.set()
        self._thread.join()
        if self._stream:
            self._stream.close()
        self._stream = None
        self._queue = None
        self._thread = None
        self._stop = None

    async def play(self, data):
        return await self._queue.async_q.put(data)

    def stop(self):
        if self._queue and self._queue.async_q:
            while not self._queue.async_q.empty():
                try:
                    self._queue.async_q.get_nowait()
                except janus.QueueEmpty:
                    break
        # Drain any items already in the sync queue to prevent further playback
        if (
            self._queue
            and hasattr(self._queue, "sync_q")
            and self._queue.sync_q is not None
        ):
            try:
                while True:
                    self._queue.sync_q.get_nowait()
            except queue.Empty:
                pass
        # If using browser output, instruct clients to stop playback immediately
        if self.browser_output and socketio:
            try:
                socketio.emit("stop_audio_output")
            except Exception as e:
                logger.error(f"Error emitting stop_audio_output: {e}")


def _play(audio_out, stream, stop, browser_output=False):
    # Sequence counter for browser audio chunks
    seq = 0
    while not stop.is_set():
        try:
            data = audio_out.sync_q.get(True, 0.05)

            # If browser output is enabled, send audio to browser via WebSocket
            if browser_output and socketio:
                try:
                    # Send audio data to browser clients with sample rate information
                    socketio.emit(
                        "audio_output",
                        {
                            "audio": data,
                            "sampleRate": AGENT_AUDIO_SAMPLE_RATE,
                            "seq": seq,
                        },
                    )
                    seq += 1
                except Exception as e:
                    logger.error(f"Error sending audio to browser: {e}")

            elif not browser_output and stream is not None:
                stream.write(data)
        except queue.Empty:
            pass


async def inject_agent_message(ws, inject_message):
    """Simple helper to inject an agent message."""
    logger.info(f"Sending InjectAgentMessage: {json.dumps(inject_message)}")
    await ws.send(json.dumps(inject_message))


async def close_websocket_with_timeout(ws, timeout=5):
    """Close websocket with timeout to avoid hanging if no close frame is received."""
    try:
        await asyncio.wait_for(ws.close(), timeout=timeout)
    except Exception as e:
        logger.error(f"Error during websocket closure: {e}")


async def wait_for_farewell_completion(ws, speaker, inject_message):
    """Wait for the farewell message to be spoken completely by the agent."""
    # Send the farewell message
    await inject_agent_message(ws, inject_message)

    # First wait for either AgentStartedSpeaking or matching ConversationText
    speaking_started = False
    while not speaking_started:
        message = await ws.recv()
        if isinstance(message, bytes):
            await speaker.play(message)
            continue

        try:
            message_json = json.loads(message)
            logger.info(f"Server: {message}")
            if message_json.get("type") == "AgentStartedSpeaking" or (
                message_json.get("type") == "ConversationText"
                and message_json.get("role") == "assistant"
                and message_json.get("content") == inject_message["message"]
            ):
                speaking_started = True
        except json.JSONDecodeError:
            continue

    # Then wait for AgentAudioDone
    audio_done = False
    while not audio_done:
        message = await ws.recv()
        if isinstance(message, bytes):
            await speaker.play(message)
            continue

        try:
            message_json = json.loads(message)
            logger.info(f"Server: {message}")
            if message_json.get("type") == "AgentAudioDone":
                audio_done = True
        except json.JSONDecodeError:
            continue

    # Give audio time to play completely
    await asyncio.sleep(3.5)


# Get available audio devices
def get_audio_devices():
    try:
        audio = pyaudio.PyAudio()
        info = audio.get_host_api_info_by_index(0)
        numdevices = info.get("deviceCount")

        input_devices = []
        for i in range(0, numdevices):
            device_info = audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get("maxInputChannels") > 0:
                input_devices.append({"index": i, "name": device_info.get("name")})

        audio.terminate()
        return input_devices
    except Exception as e:
        logger.error(f"Error getting audio devices: {e}")
        return []


# Flask routes
@app.route("/")
def index():
    # Get the sample data from MOCK_DATA
    sample_data = MOCK_DATA.get("sample_data", [])
    return render_template("index.html", sample_data=sample_data)


@app.route("/audio-devices")
def audio_devices():
    # Get available audio devices
    devices = get_audio_devices()
    return {"devices": devices}


@app.route("/industries")
def get_industries():
    # Get available industries from AgentTemplates
    return AgentTemplates.get_available_industries()


@app.route("/tts-models")
def get_tts_models():
    # Get TTS models from Deepgram API
    try:
        dg_api_key = os.environ.get("DEEPGRAM_API_KEY")
        if not dg_api_key:
            return jsonify({"error": "DEEPGRAM_API_KEY not set"}), 500

        response = requests.get(
            "https://api.deepgram.com/v1/models",
            headers={"Authorization": f"Token {dg_api_key}"},
        )

        if response.status_code != 200:
            return (
                jsonify(
                    {"error": f"API request failed with status {response.status_code}"}
                ),
                500,
            )

        data = response.json()

        # Process TTS models
        formatted_models = []

        # Check if 'tts' key exists in the response
        if "tts" in data:
            # Filter for only aura-2 models
            for model in data["tts"]:
                if model.get("architecture") == "aura-2":
                    # Extract language from languages array if available
                    language = "en"
                    if model.get("languages") and len(model.get("languages")) > 0:
                        language = model["languages"][0]

                    # Extract metadata for additional information
                    metadata = model.get("metadata", {})
                    accent = metadata.get("accent", "")
                    tags = ", ".join(metadata.get("tags", []))

                    formatted_models.append(
                        {
                            "name": model.get("canonical_name", model.get("name")),
                            "display_name": model.get("name"),
                            "language": language,
                            "accent": accent,
                            "tags": tags,
                            "description": f"{accent} accent. {tags}",
                        }
                    )

        return jsonify({"models": formatted_models})
    except Exception as e:
        logger.error(f"Error fetching TTS models: {e}")
        return jsonify({"error": str(e)}), 500


voice_agent = None


def run_async_voice_agent():
    try:
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Set the loop in the voice agent
        voice_agent.set_loop(loop)

        try:
            # Run the voice agent
            loop.run_until_complete(voice_agent.run())
        except asyncio.CancelledError:
            logger.info("Voice agent task was cancelled")
        except Exception as e:
            logger.error(f"Error in voice agent thread: {e}")
        finally:
            # Clean up the loop
            try:
                # Cancel all running tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()

                # Allow cancelled tasks to complete
                if pending:
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )

                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                loop.close()
    except Exception as e:
        logger.error(f"Error in voice agent thread setup: {e}")


@socketio.on("start_voice_agent")
def handle_start_voice_agent(data=None):
    global voice_agent
    logger.info(f"Starting voice agent with data: {data}")
    if voice_agent is None:
        # Get industry from data or default to deepgram
        industry = data.get("industry", "deepgram") if data else "deepgram"
        voiceModel = (
            data.get("voiceModel", "aura-2-thalia-en") if data else "aura-2-thalia-en"
        )
        # Get voice name from data or default to empty string, which uses the Model's voice name in the backend
        voiceName = data.get("voiceName", "") if data else ""
        # Get language from data or default to en (used in agent config)
        language = data.get("language", "en") if data else "en"
        # Check if browser is handling audio capture
        browser_audio = data.get("browserAudio", False) if data else False

        voice_agent = VoiceAgent(
            industry=industry,
            voiceModel=voiceModel,
            voiceName=voiceName,
            language=language,
            browser_audio=browser_audio,
        )
        if data:
            voice_agent.input_device_id = data.get("inputDeviceId")
            voice_agent.output_device_id = data.get("outputDeviceId")
        # Start the voice agent in a native OS thread to isolate asyncio from eventlet
        threading.Thread(target=run_async_voice_agent, daemon=True).start()


@socketio.on("stop_voice_agent")
def handle_stop_voice_agent():
    global voice_agent
    if voice_agent:
        voice_agent.is_running = False
        if voice_agent.loop and not voice_agent.loop.is_closed():
            try:
                # Cancel all running tasks
                for task in asyncio.all_tasks(voice_agent.loop):
                    task.cancel()
            except Exception as e:
                logger.error(f"Error stopping voice agent: {e}")
        voice_agent = None


@socketio.on("audio_data")
def handle_audio_data(data):
    global voice_agent
    if voice_agent and voice_agent.is_running and voice_agent.browser_audio:
        try:
            # Get the audio buffer and sample rate
            audio_buffer = data.get("audio")
            sample_rate = data.get(
                "sampleRate", 44100
            )  # Default to 44.1kHz if not specified

            if audio_buffer:
                try:
                    # Convert the binary data to bytes
                    # Socket.IO binary data can come as either memoryview or bytes
                    if isinstance(audio_buffer, memoryview):
                        # Convert memoryview to bytes
                        audio_bytes = audio_buffer.tobytes()

                        # Log detailed info about the first chunk
                        if not hasattr(handle_audio_data, "first_log_done"):
                            import numpy as np

                            # Peek at the data to verify it's in the right format
                            int16_peek = np.frombuffer(
                                audio_buffer[:20], dtype=np.int16
                            )
                            logger.info(f"First few samples: {int16_peek}")
                    elif isinstance(audio_buffer, bytes):
                        # Already bytes, use directly
                        audio_bytes = audio_buffer
                    else:
                        # Unexpected type, try to convert and log a warning
                        logger.warning(
                            f"Unexpected audio buffer type: {type(audio_buffer)}"
                        )
                        try:
                            audio_bytes = bytes(audio_buffer)
                        except Exception as e:
                            logger.error(
                                f"Failed to convert audio buffer to bytes: {e}"
                            )
                            return

                    # Ensure whole 16-bit samples
                    if len(audio_bytes) % 2 != 0:
                        audio_bytes = audio_bytes[:-1]

                    # Resample to 16k if needed (server-side fallback)
                    original_len = len(audio_bytes)
                    original_rate = (
                        int(sample_rate)
                        if isinstance(sample_rate, (int, float))
                        else 44100
                    )
                    resampled = False
                    if original_rate != 16000:
                        try:
                            prev_state = getattr(
                                handle_audio_data, "_ratecv_state", None
                            )
                            audio_bytes, state = audioop.ratecv(
                                audio_bytes, 2, 1, original_rate, 16000, prev_state
                            )
                            handle_audio_data._ratecv_state = state
                            sample_rate = 16000
                            resampled = True
                        except Exception as e:
                            logger.warning(
                                f"Server resample failed (rate {original_rate}->16000): {e}. Passing through original bytes."
                            )

                    # Log the first time we receive audio data
                    if not hasattr(handle_audio_data, "first_log_done"):
                        logger.info(
                            f"Received first browser audio chunk: in_len={original_len} bytes, in_rate={original_rate}Hz, out_len={len(audio_bytes)} bytes, out_rate={sample_rate}Hz, resampled={resampled}"
                        )
                        handle_audio_data.first_log_done = True

                    # Put the audio data in the queue for processing
                    if voice_agent.loop and not voice_agent.loop.is_closed():
                        asyncio.run_coroutine_threadsafe(
                            voice_agent.mic_audio_queue.put(audio_bytes),
                            voice_agent.loop,
                        )
                except Exception as e:
                    logger.error(
                        f"Error converting audio buffer: {e}, type: {type(audio_buffer)}"
                    )
                    import traceback

                    logger.error(traceback.format_exc())
        except Exception as e:
            logger.error(f"Error processing browser audio data: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Voice Agent Demo Starting!")
    print("=" * 60)
    print("\n1. Open this link in your browser to start the demo:")
    print("   http://127.0.0.1:5000")
    print("\n2. Click 'Start Voice Agent' when the page loads")
    print("\n3. Speak with the agent using your microphone")
    print("\nPress Ctrl+C to stop the server\n")
    print("=" * 60 + "\n")

    socketio.run(app, debug=True)
