import re

class Preprocessor:
    def __init__(self):
        self.arab_signs = re.compile(
r'''
    [
        \u0610-\u061A  
        \u064B-\u065F   
        \u0670          
        \u06D6-\u06DC   
        \u06DF-\u06E8
        \u06EA-\u06ED
        \u0640 
    ]
'''        
)
        # anything that is continous non-arabic text
        self.non_arab = r'''
        (
            [^  \u0600-\u06FF
                \u0750-\u077F
                \u08A0-\u08FF
                \uFB50-\uFDFF
                \uFE70-\uFEFF
                \(\)\.
            ]+
        )
    '''
        self.letter_normalizer = {
    'إ': 'ا', 'أ': 'ا', 'آ': 'ا',
    'ى': 'ي',
    'ئ': 'ي',    
    'ة': 'ه',
    'ټ': 'ت',
    }

    def normalize_arabic(self, text,signs_pattern,normalizer) -> str:
        # 1) strip tashkīl & tatwīl
        txt = signs_pattern.sub("", text)
        # 2) apply normalization map
        _norm_re = re.compile("|".join(map(re.escape, normalizer.keys())))
        
        return _norm_re.sub(lambda m: normalizer[m.group()], txt)

    def convert_arabic_digits_to_english(self, text):
        arabic_to_english_digits = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        return text.translate(arabic_to_english_digits)

    def extract_non_arabic_from_str(self, text, pattern):
        temp = re.findall(pattern,text,re.VERBOSE|re.MULTILINE)
        filtered = [item.strip() for item in temp if item != " "]
        return filtered
    
    def extract_non_arabic_in_list(self,tokens_list):
        list_of_english_tokens = [self.extract_non_arabic_from_str(token, self.non_arab) for token in tokens_list]
        flat_list = [item for sublist in list_of_english_tokens for item in sublist]
        english_tokens = [token for token in flat_list if token != "+"]
        return english_tokens
    
    def normalize_and_convert_digits(self,tokens_list):
        tokens_list    = [self.convert_arabic_digits_to_english(token) for token in tokens_list]
        tokens_list    = [self.normalize_arabic(token,self.arab_signs, self.letter_normalizer) for token in tokens_list]
        return tokens_list
    
    def mask_non_arabic_text(self, text, pattern):
        return pattern.sub(" <ENG> ", text)
        
        
    
    def mask_non_arabic_tokens(self, tokens_list, english_tokens):

        if not english_tokens:
            return tokens_list
        
        unique_english = sorted(set(english_tokens), key=len, reverse=True)
        pattern = re.compile(r'(' + '|'.join(map(re.escape, unique_english)) + r')', re.VERBOSE | re.MULTILINE)
        tokens_str = " ".join(tokens_list)
        
        return self.mask_non_arabic_text(tokens_str, pattern).split()