import logging
import sys
import json
import boto3
import os

logging.basicConfig(
    level=logging.INFO,  # Default to INFO level
    format='%(filename)s:%(lineno)d | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger("utils")

def load_config():
    config = None
    
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    return config

config = load_config()

bedrock_region = config['region']
projectName = config['projectName']
sharing_url = config['sharing_url']
s3_bucket = config['s3_bucket']
s3_arn = config['s3_arn']
opensearch_url = config['opensearch_url']
collectionArn = config['collectionArn']
knowledge_base_role = config['knowledge_base_role']
opensearch_url = config['opensearch_url']

def load_mcp_env():
    with open("mcp.env", "r", encoding="utf-8") as f:
        mcp_env = json.load(f)
    return mcp_env

def save_mcp_env(mcp_env):
    with open("mcp.env", "w", encoding="utf-8") as f:
        json.dump(mcp_env, f)
