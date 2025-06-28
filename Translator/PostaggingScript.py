import pandas as pd 
from collections import Counter
from Preprocessing import Preprocessor
import farasa
from farasa.segmenter import FarasaSegmenter
from farasa.stemmer import FarasaStemmer
from farasa.pos import FarasaPOSTagger 
from multiprocessing import Pool, cpu_count
import pandas as pd
from tqdm import tqdm

tqdm.monitor_interval = 0  # avoid warning


import json

def process_instruction(instr):
    pos_tagger = FarasaPOSTagger()
    return pos_tagger.tag_segments(instr)


if __name__ == "__main__":
    test_data = pd.read_csv("./train_data.csv")
    instructions =test_data.tolist()

    with Pool(processes=10) as pool:
        results = list(tqdm(pool.imap(process_instruction, instructions), total=len(instructions)))
    test = pd.Series(results)
    test.to_pickle("./train_12000.pkl")
    