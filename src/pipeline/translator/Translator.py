import json
import requests
from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0

def is_arabic_language(text: str) -> bool:
    try:
        lang = detect(text)
        return lang == 'ar'
    except:
        return False
    
# using mymemory to generate the Arabic Training Data
def translate(text):
        if(is_arabic_language(text)):
            url = "https://api.mymemory.translated.net/get"
            params = {
                "q": text,
                "langpair": "ar|en",
                "key": "43a221557ce746042181",
                "de": "abdohefney1@gmail.com"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("responseStatus") != 200:
                raise Exception(f"MyMemory error: {data.get('responseDetails', 'Unknown error')}")
            
            return data["responseData"]["translatedText"]
        else: 
             return text

if __name__ == '__main__':
    samples = [
        "Hello, world!",                    # 100% English → False
        "مرحبا بالعالم",                    # 100% Arabic  → True
        "Hello مرحبا",                     # 50% English, 50% Arabic → True
        "This is a mix مرحبا and English",  # mixed
        "1234!@#$",                         # no letters → False
    ]
    for s in samples:
        print(f"'{s}': {is_arabic_language(s)}")