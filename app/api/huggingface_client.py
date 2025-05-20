import os
import json
import requests
from typing import List, Dict, Any, Optional, Union
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

# Import the generation parameters configuration
from app.utils.generation_config import get_config_manager, get_generation_params

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

@dataclass
class ChatCompletionMessage:
    """Class to represent a chat message similar to OpenAI's format."""
    content: str
    role: str

@dataclass
class ChatCompletionChoice:
    """Class to represent a chat completion choice similar to OpenAI's format."""
    message: ChatCompletionMessage
    finish_reason: str = "stop"
    index: int = 0

@dataclass
class ChatCompletion:
    """Class to represent a chat completion response similar to OpenAI's format."""
    id: str
    choices: List[ChatCompletionChoice]
    model: str
    created: int
    object: str = "chat.completion"

class HuggingFaceClient:
    """Client for accessing HuggingFace models via the Inference API.
    
    This class is designed to mimic the OpenAI client interface for easy integration.
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api-inference.huggingface.co/models"):
        """Initialize the HuggingFace client.
        
        Args:
            api_key: HuggingFace API token
            base_url: Base URL for the HuggingFace Inference API
        """
        self.api_key = api_key or os.getenv("HUGGINGFACE_API_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
        if not self.api_key:
            logger.warning("No HuggingFace API token provided. Some functionality may be limited.")
            
        self.base_url = base_url
        self.chat = self.ChatCompletions(self)
        
        # Get the configuration manager
        self.config_manager = get_config_manager()
    
    def _load_config(self) -> Dict:
        """Load model configuration from the config file."""
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   "config", "model_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load config file: {str(e)}")
        
        return {}
    
    class ChatCompletions:
        """Nested class to mimic OpenAI's chat completions interface."""
        
        def __init__(self, client):
            """Initialize with reference to parent client."""
            self.client = client
        
        def create(
            self, 
            messages: List[Dict[str, str]], 
            model: str = None,
            temperature: float = None,
            max_tokens: int = None,
            top_p: float = None,
            frequency_penalty: float = None,
            presence_penalty: float = None,
            stop: Optional[Union[str, List[str]]] = None,
            timeout: int = 120,
            **kwargs
        ) -> ChatCompletion:
            """Create a chat completion using HuggingFace models.
            
            Args:
                messages: List of message dictionaries with role and content
                model: HuggingFace model ID to use
                temperature: Sampling temperature (0-1)
                max_tokens: Maximum number of tokens to generate
                top_p: Nucleus sampling parameter
                frequency_penalty: Not directly used by HuggingFace but included for compatibility
                presence_penalty: Not directly used by HuggingFace but included for compatibility
                stop: Optional string or list of strings where the model should stop generating
                timeout: Request timeout in seconds
                **kwargs: Additional parameters to pass to the model
                
            Returns:
                ChatCompletion object with response
            """
            # Get the current LLM model if not specified
            if model is None:
                model = self.client.config_manager.get_llm_model()
            
            # Get generation parameters from the configuration manager
            params = get_generation_params("huggingface")
            
            # Use provided parameters or those from config
            temperature = temperature if temperature is not None else params.get("temperature", 0.3)
            max_tokens = max_tokens if max_tokens is not None else params.get("max_tokens", 4000)
            top_p = top_p if top_p is not None else params.get("top_p", 0.85)
            
            # Prepare headers with API token
            headers = {
                "Authorization": f"Bearer {self.client.api_key}",
                "Content-Type": "application/json"
            }
            
            # Process the messages and create prompt according to model's expected format
            prompt = self._format_prompt(messages, model)
            
            # Prepare payload according to HuggingFace Inference API
            payload = {
                "inputs": prompt,
                "parameters": {
                    "temperature": temperature,
                    "max_new_tokens": max_tokens,
                    "top_p": top_p,
                    "do_sample": temperature > 0,
                    "return_full_text": False  # Only return the generated text, not the prompt
                }
            }
            
            # Add stop sequences if provided
            if stop:
                if isinstance(stop, str):
                    payload["parameters"]["stop"] = [stop]
                else:
                    payload["parameters"]["stop"] = stop
            
            # Add any additional parameters
            for key, value in kwargs.items():
                if key not in payload["parameters"]:
                    payload["parameters"][key] = value
            
            # Log info about the API call
            logger.info(f"Calling HuggingFace Inference API with model: {model}")
            
            # Log debugging information (more detailed payload)
            logger.debug(f"Sending request to {model} with payload: {payload}")
            
            try:
                # Make the API request
                response = requests.post(
                    f"{self.client.base_url}/{model}",
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                
                # Check for errors
                response.raise_for_status()
                
                # Parse the response
                result = response.json()
                logger.debug(f"Received response: {result}")
                
                # Extract the generated text
                if isinstance(result, list) and len(result) > 0:
                    if "generated_text" in result[0]:
                        generated_text = result[0]["generated_text"]
                    else:
                        # Some models might return a different format
                        generated_text = result[0]
                else:
                    # Handle unexpected response format
                    logger.warning(f"Unexpected response format: {result}")
                    generated_text = str(result)
                
                # Log successful response
                logger.info(f"Successfully received response from model: {model}")
                
                # Create a ChatCompletion object
                return ChatCompletion(
                    id=f"hf-{model.replace('/', '-')}-{id(result)}",
                    choices=[
                        ChatCompletionChoice(
                            message=ChatCompletionMessage(
                                content=generated_text,
                                role="assistant"
                            )
                        )
                    ],
                    model=model,
                    created=int(response.headers.get("Date-Created", 0))
                )
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error calling HuggingFace API: {str(e)}")
                # Create an error response
                error_msg = f"HuggingFace API error: {str(e)}"
                return ChatCompletion(
                    id=f"error-{id(e)}",
                    choices=[
                        ChatCompletionChoice(
                            message=ChatCompletionMessage(
                                content=error_msg,
                                role="assistant"
                            ),
                            finish_reason="error"
                        )
                    ],
                    model=model,
                    created=0
                )
        
        def _format_prompt(self, messages: List[Dict[str, str]], model: str) -> str:
            """Format messages into a prompt suitable for the specified model.
            
            Different models have different expected formats, so we need to handle each case.
            
            Args:
                messages: List of message dictionaries
                model: Model name to format for
                
            Returns:
                Formatted prompt string
            """
            if model.startswith("meta-llama/Llama-3"):
                return self._format_llama3_prompt(messages)
            elif model.startswith("mistralai/Mistral"):
                return self._format_mistral_prompt(messages)
            elif model.startswith("tiiuae/falcon"):
                return self._format_falcon_prompt(messages)
            else:
                # Default format for unknown models (simple concatenation)
                return self._format_default_prompt(messages)
        
        def _format_llama3_prompt(self, messages: List[Dict[str, str]]) -> str:
            """Format messages for Llama 3 models.
            
            Llama 3 expects:
            <|begin_of_text|><|start_header_id|>system<|end_header_id|>
            {system_prompt}<|eot_id|>
            <|start_header_id|>user<|end_header_id|>
            {user_message}<|eot_id|>
            <|start_header_id|>assistant<|end_header_id|>
            
            Args:
                messages: List of message dictionaries
                
            Returns:
                Formatted prompt string
            """
            prompt = ""
            for message in messages:
                role = message.get("role", "").lower()
                content = message.get("content", "")
                
                if role == "system":
                    prompt += f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{content}<|eot_id|>\n"
                elif role == "user":
                    prompt += f"<|start_header_id|>user<|end_header_id|>\n{content}<|eot_id|>\n"
                elif role == "assistant":
                    prompt += f"<|start_header_id|>assistant<|end_header_id|>\n{content}<|eot_id|>\n"
            
            # Add final assistant token to prompt the model to generate
            prompt += "<|start_header_id|>assistant<|end_header_id|>\n"
            return prompt
        
        def _format_mistral_prompt(self, messages: List[Dict[str, str]]) -> str:
            """Format messages for Mistral models.
            
            Mistral format:
            <s>[INST] {system_prompt} {user_message} [/INST] {assistant_message}</s>
            
            Args:
                messages: List of message dictionaries
                
            Returns:
                Formatted prompt string
            """
            system_prompt = ""
            conversation = []
            
            for message in messages:
                role = message.get("role", "").lower()
                content = message.get("content", "")
                
                if role == "system":
                    system_prompt = content
                elif role == "user":
                    if system_prompt:
                        conversation.append(f"<s>[INST] {system_prompt}\n\n{content} [/INST]")
                        system_prompt = ""  # Only use system prompt for the first user message
                    else:
                        conversation.append(f"<s>[INST] {content} [/INST]")
                elif role == "assistant":
                    # Complete the last user message with assistant response
                    if conversation:
                        conversation[-1] += f" {content}</s>"
                    else:
                        # If there's an assistant message without a preceding user message
                        conversation.append(f"<s>{content}</s>")
            
            # If the last message was from a user and doesn't have a response yet
            if conversation and not conversation[-1].endswith("</s>"):
                # Don't add anything, leave it open for generation
                pass
                
            return "\n".join(conversation)
        
        def _format_falcon_prompt(self, messages: List[Dict[str, str]]) -> str:
            """Format messages for Falcon models.
            
            Falcon format:
            System: {system_prompt}
            User: {user_message}
            Assistant: {assistant_message}
            
            Args:
                messages: List of message dictionaries
                
            Returns:
                Formatted prompt string
            """
            prompt = ""
            
            for message in messages:
                role = message.get("role", "").lower()
                content = message.get("content", "")
                
                if role == "system":
                    prompt += f"System: {content}\n\n"
                elif role == "user":
                    prompt += f"User: {content}\n\n"
                elif role == "assistant":
                    prompt += f"Assistant: {content}\n\n"
            
            # Add final assistant prompt
            if not prompt.endswith("Assistant: "):
                prompt += "Assistant: "
                
            return prompt
        
        def _format_default_prompt(self, messages: List[Dict[str, str]]) -> str:
            """Default format for unknown models.
            
            Args:
                messages: List of message dictionaries
                
            Returns:
                Formatted prompt string
            """
            prompt = ""
            
            for message in messages:
                role = message.get("role", "").lower()
                content = message.get("content", "")
                
                prompt += f"{role.capitalize()}: {content}\n\n"
            
            # Add assistant prompt to generate response
            prompt += "Assistant: "
            return prompt

# Create a function to get the client with default parameters
def get_huggingface_client(api_key: Optional[str] = None) -> HuggingFaceClient:
    """Create a HuggingFace client with the provided or environment API key.
    
    Args:
        api_key: Optional API key (if not provided, will use HUGGINGFACE_API_TOKEN from env)
        
    Returns:
        HuggingFaceClient instance
    """
    return HuggingFaceClient(api_key=api_key) 