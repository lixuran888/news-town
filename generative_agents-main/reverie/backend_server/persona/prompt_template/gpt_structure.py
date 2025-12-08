"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: gpt_structure.py
Description: Wrapper functions for calling OpenAI APIs.
"""
import json
import random
import openai
import time 
import threading
from functools import wraps

from utils import *

# ============================================================================
# LLM API 配置 - 支持本地模型和云端 API
# ============================================================================

# 根据配置选择使用本地模型还是云端 API
if USE_LOCAL_MODEL:
    # 使用本地模型（如 Ollama、vLLM 等）
    openai.api_base = LOCAL_API_BASE
    openai.api_key = LOCAL_API_KEY if LOCAL_API_KEY else "ollama"
    current_model_name = LOCAL_MODEL_NAME
    print("=" * 60)
    print(f"[LLM Config] ✅ 当前使用: 本地模型")
    print(f"[LLM Config] 模型名称: {LOCAL_MODEL_NAME}")
    print(f"[LLM Config] API地址: {LOCAL_API_BASE}")
    print("=" * 60)
else:
    # 使用云端 API（DeepSeek）
    openai.api_base = DEEPSEEK_API_BASE
    openai.api_key = deepseek_api_key
    current_model_name = DEEPSEEK_MODEL_NAME
    print("=" * 60)
    print(f"[LLM Config] ✅ 当前使用: 云端API")
    print(f"[LLM Config] 模型名称: {DEEPSEEK_MODEL_NAME}")
    print(f"[LLM Config] API地址: {DEEPSEEK_API_BASE}")
    print("=" * 60)

def temp_sleep(seconds=0.1):
  time.sleep(seconds)

def _api_call_with_timeout(api_func, timeout):
  """使用threading实现超时的API调用"""
  result = [None]
  exception = [None]
  
  def api_wrapper():
    try:
      result[0] = api_func()
    except Exception as e:
      exception[0] = e
  
  thread = threading.Thread(target=api_wrapper)
  thread.daemon = True
  thread.start()
  thread.join(timeout)
  
  if thread.is_alive():
    # 超时了，但无法强制停止线程，只能返回超时错误
    return None, TimeoutError(f"API调用超时（>{timeout}秒）")
  
  if exception[0]:
    return None, exception[0]
  
  return result[0], None

def ChatGPT_single_request(prompt, timeout=None): 
  """
  发送单个请求到LLM API，支持超时设置
  
  Args:
    prompt: 提示词
    timeout: 超时时间（秒），如果为None则使用配置的LLM_TIMEOUT
  """
  if timeout is None:
    timeout = LLM_TIMEOUT
  
  temp_sleep()

  start_time = time.time()
  
  def make_api_call():
    try:
      # 尝试使用timeout参数（如果openai库支持）
      return openai.ChatCompletion.create(
        model=current_model_name, 
        messages=[{"role": "user", "content": prompt}],
        timeout=timeout
      )
    except TypeError:
      # 如果不支持timeout参数，不使用它
      return openai.ChatCompletion.create(
        model=current_model_name, 
        messages=[{"role": "user", "content": prompt}]
      )
  
  try:
    completion, error = _api_call_with_timeout(make_api_call, timeout)
    
    if error:
      if isinstance(error, TimeoutError):
        error_msg = f"API调用超时（>{timeout}秒）"
        print(f"[{current_model_name}] {error_msg}")
        return f"[超时] {error_msg}"
      else:
        raise error
    
    if completion is None:
      error_msg = f"API调用超时（>{timeout}秒）"
      print(f"[{current_model_name}] {error_msg}")
      return f"[超时] {error_msg}"
    
    result = completion["choices"][0]["message"]["content"]
    
    elapsed = time.time() - start_time
    if elapsed > 5:  # 如果超过5秒，打印警告
      print(f"[LLM] 响应时间: {elapsed:.2f}秒")
    
    return result
    
  except Exception as e:
    error_msg = f"LLM API ERROR: {str(e)}"
    print(f"[{current_model_name}] {error_msg}")
    # 如果是连接错误，返回一个默认响应而不是错误信息
    if "connection" in str(e).lower() or "timeout" in str(e).lower() or "refused" in str(e).lower():
      return f"[连接错误] 无法连接到模型服务，请检查 {LOCAL_API_BASE if USE_LOCAL_MODEL else DEEPSEEK_API_BASE} 是否正常运行"
    return error_msg


# ============================================================================
# #####################[SECTION 1: CHATGPT-3 STRUCTURE] ######################
# ============================================================================

def GPT4_request(prompt): 
  """
  Given a prompt and a dictionary of GPT parameters, make a request to OpenAI
  server and returns the response. 
  ARGS:
    prompt: a str prompt
    gpt_parameter: a python dictionary with the keys indicating the names of  
                   the parameter and the values indicating the parameter 
                   values.   
  RETURNS: 
    a str of GPT-3's response. 
  """
  temp_sleep()

  try: 
    completion = openai.ChatCompletion.create(
    model=current_model_name, 
    messages=[{"role": "user", "content": prompt}]
    )
    return completion["choices"][0]["message"]["content"]
  
  except Exception as e: 
    error_msg = f"LLM API ERROR: {str(e)}"
    print(f"[{current_model_name}] {error_msg}")
    return error_msg


def ChatGPT_request(prompt): 
  """
  Given a prompt and a dictionary of GPT parameters, make a request to OpenAI
  server and returns the response. 
  ARGS:
    prompt: a str prompt
    gpt_parameter: a python dictionary with the keys indicating the names of  
                   the parameter and the values indicating the parameter 
                   values.   
  RETURNS: 
    a str of GPT-3's response. 
  """
  # temp_sleep()
  try: 
    completion = openai.ChatCompletion.create(
    model=current_model_name, 
    messages=[{"role": "user", "content": prompt}]
    )
    return completion["choices"][0]["message"]["content"]
  
  except Exception as e: 
    error_msg = f"LLM API ERROR: {str(e)}"
    print(f"[{current_model_name}] {error_msg}")
    return error_msg


def GPT4_safe_generate_response(prompt, 
                                   example_output,
                                   special_instruction,
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False): 
  prompt = 'GPT-3 Prompt:\n"""\n' + prompt + '\n"""\n'
  prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
  prompt += "Example output json:\n"
  prompt += '{"output": "' + str(example_output) + '"}'

  if verbose: 
    print ("CHAT GPT PROMPT")
    print (prompt)

  for i in range(repeat): 

    try: 
      curr_gpt_response = GPT4_request(prompt).strip()
      end_index = curr_gpt_response.rfind('}') + 1
      curr_gpt_response = curr_gpt_response[:end_index]
      curr_gpt_response = json.loads(curr_gpt_response)["output"]
      
      if func_validate(curr_gpt_response, prompt=prompt): 
        return func_clean_up(curr_gpt_response, prompt=prompt)
      
      if verbose: 
        print ("---- repeat count: \n", i, curr_gpt_response)
        print (curr_gpt_response)
        print ("~~~~")

    except: 
      pass

  return False


def ChatGPT_safe_generate_response(prompt, 
                                   example_output,
                                   special_instruction,
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False): 
  # prompt = 'GPT-3 Prompt:\n"""\n' + prompt + '\n"""\n'
  prompt = '"""\n' + prompt + '\n"""\n'
  prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
  prompt += "Example output json:\n"
  prompt += '{"output": "' + str(example_output) + '"}'

  if verbose: 
    print ("CHAT GPT PROMPT")
    print (prompt)

  for i in range(repeat): 

    try: 
      curr_gpt_response = ChatGPT_request(prompt).strip()
      end_index = curr_gpt_response.rfind('}') + 1
      curr_gpt_response = curr_gpt_response[:end_index]
      curr_gpt_response = json.loads(curr_gpt_response)["output"]

      # print ("---ashdfaf")
      # print (curr_gpt_response)
      # print ("000asdfhia")
      
      if func_validate(curr_gpt_response, prompt=prompt): 
        return func_clean_up(curr_gpt_response, prompt=prompt)
      
      if verbose: 
        print ("---- repeat count: \n", i, curr_gpt_response)
        print (curr_gpt_response)
        print ("~~~~")

    except: 
      pass

  return False


def ChatGPT_safe_generate_response_OLD(prompt, 
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False): 
  if verbose: 
    print ("CHAT GPT PROMPT")
    print (prompt)

  for i in range(repeat): 
    try: 
      curr_gpt_response = ChatGPT_request(prompt).strip()
      if func_validate(curr_gpt_response, prompt=prompt): 
        return func_clean_up(curr_gpt_response, prompt=prompt)
      if verbose: 
        print (f"---- repeat count: {i}")
        print (curr_gpt_response)
        print ("~~~~")

    except: 
      pass
  print ("FAIL SAFE TRIGGERED") 
  return fail_safe_response


# ============================================================================
# ###################[SECTION 2: ORIGINAL GPT-3 STRUCTURE] ###################
# ============================================================================

def GPT_request(prompt, gpt_parameter): 
  """
  Given a prompt and a dictionary of GPT parameters, make a request to OpenAI
  server and returns the response. 
  ARGS:
    prompt: a str prompt
    gpt_parameter: a python dictionary with the keys indicating the names of  
                   the parameter and the values indicating the parameter 
                   values.   
  RETURNS: 
    a str of GPT-3's response. 
  """
  temp_sleep()

  # 为适配 DeepSeek 的 OpenAI 兼容接口，这里统一通过 ChatCompletion
  # 调用 deepseek-chat，而不再使用旧的 Completion.create/text-davinci-003。
  # 同时对 prompt 做一次简单截断，避免极端长文本直接触发 token 上限。
  if isinstance(prompt, str):
    max_chars = 8000  # 粗略字符上限，对应大致的 token 限制
    if len(prompt) > max_chars:
      # 保留开头的指令、人设和格式说明，截断末尾冗长部分。
      prompt = prompt[:max_chars]

  try:
    completion = openai.ChatCompletion.create(
      model=current_model_name,
      messages=[{"role": "user", "content": prompt}],
      max_tokens=gpt_parameter.get("max_tokens", 128),
      temperature=gpt_parameter.get("temperature", 0.7),
      top_p=gpt_parameter.get("top_p", 1),
    )
    return completion["choices"][0]["message"]["content"]
  except Exception as e:
    # 兼容旧日志格式，同时输出真实异常信息，便于后续排查。
    error_msg = f"TOKEN LIMIT EXCEEDED / LLM ERROR: {str(e)}"
    print(f"[{current_model_name}] {error_msg}")
    return "TOKEN LIMIT EXCEEDED"


def generate_prompt(curr_input, prompt_lib_file): 
  """
  Takes in the current input (e.g. comment that you want to classifiy) and 
  the path to a prompt file. The prompt file contains the raw str prompt that
  will be used, which contains the following substr: !<INPUT>! -- this 
  function replaces this substr with the actual curr_input to produce the 
  final promopt that will be sent to the GPT3 server. 
  ARGS:
    curr_input: the input we want to feed in (IF THERE ARE MORE THAN ONE
                INPUT, THIS CAN BE A LIST.)
    prompt_lib_file: the path to the promopt file. 
  RETURNS: 
    a str prompt that will be sent to OpenAI's GPT server.  
  """
  if type(curr_input) == type("string"): 
    curr_input = [curr_input]
  curr_input = [str(i) for i in curr_input]

  f = open(prompt_lib_file, "r")
  prompt = f.read()
  f.close()
  for count, i in enumerate(curr_input):   
    prompt = prompt.replace(f"!<INPUT {count}>!", i)
  if "<commentblockmarker>###</commentblockmarker>" in prompt: 
    prompt = prompt.split("<commentblockmarker>###</commentblockmarker>")[1]
  return prompt.strip()


def safe_generate_response(prompt, 
                           gpt_parameter,
                           repeat=1,
                           fail_safe_response="error",
                           func_validate=None,
                           func_clean_up=None,
                           verbose=False): 
  if verbose: 
    print (prompt)

  # 为了避免在 DeepSeek 频繁报错时长时间卡住，这里强制只请求一次。
  # 即便上层传入更大的 repeat，也会被限制为 1。
  repeat = 1

  for i in range(repeat): 
    curr_gpt_response = GPT_request(prompt, gpt_parameter)

    # 统一过滤 DeepSeek 返回的错误字符串，避免污染世界线。
    # 一旦检测到错误，立刻降级到 fail_safe_response，并明确打印日志。
    if isinstance(curr_gpt_response, str) and (
        "TOKEN LIMIT EXCEEDED" in curr_gpt_response or
        "DeepSeek API ERROR" in curr_gpt_response
    ):
      print("[LLM FILTER] TOKEN LIMIT EXCEEDED / DeepSeek API ERROR, "
            "downgrade to fail_safe_response")
      return fail_safe_response

    if func_validate(curr_gpt_response, prompt=prompt): 
      return func_clean_up(curr_gpt_response, prompt=prompt)
    if verbose: 
      print ("---- repeat count: ", i, curr_gpt_response)
      print (curr_gpt_response)
      print ("~~~~")
  return fail_safe_response


def get_embedding(text, model="text-embedding-ada-002"):
  text = text.replace("\n", " ")
  if not text: 
    text = "this is blank"
  # 注意：DeepSeek 可能不支持 embedding，如果报错需要改用其他 embedding 服务
  try:
    return openai.Embedding.create(
            input=[text], model=model)['data'][0]['embedding']
  except:
    # 如果 DeepSeek 不支持，可以返回一个默认向量或使用其他服务
    print("Warning: Embedding not supported, returning default vector")
    return [0.0] * 1536  # 默认维度，根据实际需要调整


if __name__ == '__main__':
  gpt_parameter = {"engine": "text-davinci-003", "max_tokens": 50, 
                   "temperature": 0, "top_p": 1, "stream": False,
                   "frequency_penalty": 0, "presence_penalty": 0, 
                   "stop": ['"']}
  curr_input = ["driving to a friend's house"]
  prompt_lib_file = "prompt_template/test_prompt_July5.txt"
  prompt = generate_prompt(curr_input, prompt_lib_file)

  def __func_validate(gpt_response): 
    if len(gpt_response.strip()) <= 1:
      return False
    if len(gpt_response.strip().split(" ")) > 1: 
      return False
    return True
  def __func_clean_up(gpt_response):
    cleaned_response = gpt_response.strip()
    return cleaned_response

  output = safe_generate_response(prompt, 
                                 gpt_parameter,
                                 5,
                                 "rest",
                                 __func_validate,
                                 __func_clean_up,
                                 True)

  print (output)




















