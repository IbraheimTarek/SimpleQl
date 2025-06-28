import json
import requests

# using mymemory to generate the Arabic Training Data
def translate(text):
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": text,
            "langpair": "en|ar",
            "key": "43a221557ce746042181",
            "de": "abdohefney1@gmail.com"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("responseStatus") != 200:
            raise Exception(f"MyMemory error: {data.get('responseDetails', 'Unknown error')}")
        
        return data["responseData"]["translatedText"]