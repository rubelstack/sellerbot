"""
GET YOUR PLUS — Order ID Generator
Generates unique order IDs in the format GYP-XXXXX
"""

import random
import string
from config import ORDER_PREFIX, ORDER_ID_LENGTH


def generate_order_id(existing_ids: set = None) -> str:
    """
    Generate a unique order ID like GYP-XT56K.
    
    Args:
        existing_ids: Set of existing order IDs to avoid collisions.
    
    Returns:
        A unique order ID string.
    """
    charset = string.ascii_uppercase + string.digits
    
    while True:
        suffix = ''.join(random.choices(charset, k=ORDER_ID_LENGTH))
        order_id = f"{ORDER_PREFIX}-{suffix}"
        
        if existing_ids is None or order_id not in existing_ids:
            return order_id
