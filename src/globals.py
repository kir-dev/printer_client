"""Contains global variables used by multiple modules"""

from threading import RLock
from printer import User

# Global state variable
# Accessing it should always surrounded by "with userDataLock:" 
userDataLock = RLock()
userData = User(initialized=False)
