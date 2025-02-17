import pandas as pd
import os
import json
import urllib
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.corpus import stopwords
import nltk
import re
from datetime import date

# preprocess the abstracts
def clean_abstract(abs):
    # remove unwanted patterns and convert to lower case
    sub_pattern = "\(|<|>|\)|,|:|%|\+|=|\.|\[|\]|\"|;"
    abs = [re.sub(sub_pattern,"",i).lower() for i in re.split("[\s/]", abs)]
    abs = [re.sub("/"," ", i) for i in abs]
    # remove any items in the list that are only numbers
    # remove empty strings from the lists
    remove_pattern = "(^$)|(^\d+-*\d+$)"
    rm = []
    for i in abs:
        if re.match(remove_pattern, i) is not None:
            rm.append(i)
    # removing stopwords, empty strings and numbers only
    abs = [i for i in abs if i not in rm and i not in
           stopwords.words('english') and i not in MANUALFILTER]
    # lemmatization
    abs = [WordNetLemmatizer().lemmatize(i) for i in abs]
    # remove words with just one character
    abs = [i for i in abs if len(i) > 1]
    abs = " ".join(abs)
    return abs

# extract metadata and get the newest litcovid jsons
def litcovid_get_metadata(new=False):
    # get the tsv of the document IDs
    path = "../data/litcovid_meta/" + str(DATE) + ".litcovid.export.tsv"

    if (os.path.exists(path) == False):
        # download meta file if it doesn't exist yet
        url = "https://www.ncbi.nlm.nih.gov/research/coronavirus-api/export"
        print("saving newest ID files (date: " + str(DATE) + ")")
        urllib.request.urlretrieve(url, path)
    docslist = pd.read_csv(path, sep="\t", comment="#")

    print("There are " + str(len(docslist)) + " available documents at the moment")
    index_list = docslist["pmid"]
    for id in index_list:
        path = "../data/litcovid_jsons/" + str(id) + ".json"
        if (os.path.exists(path) == False):
            # download json file if it doesn't exist yet
            url = "https://www.ncbi.nlm.nih.gov/research/coronavirus-api/publication/" + \
                str(id) + "?format=json"
            print("saving: " + str(id))
            urllib.request.urlretrieve(url, '../data/litcovid_jsons/' + str(id) + '.json')

    if new:
        meta_df = pd.DataFrame(columns=["Source", "PMID", "DOI", "Title", "Date",
                                        "Abstract", "Categories"])
    else:
        meta_df = pd.read_csv(LITCOVIDMAPPINGS, index_col=None)
    already_contained_ids = meta_df["PMID"].values
    skipped = 0
    abs_missing_or_short = 0
    print("Previous number of entries in litcovid", len(meta_df))
    for i in index_list:
        if i not in already_contained_ids:
            try:
                with open("../data/litcovid_jsons/" + str(i) + ".json") as json_file:
                    json_doc = json.load(json_file)
            except:
                json_doc = None
                # some jsons are completely empty
                skipped = skipped + 1
            if(json_doc is not None and "abstract" in json_doc.keys() and "topics" in json_doc.keys()):
                abstract = json_doc["abstract"][0]
                categories = json_doc["topics"][0]
                if (abstract is not None and len(abstract.split()) > MINLEN and categories != "NONE"):
                    # only use the first listed topic as a label now
                    # (see project proposal)
                    meta_df = meta_df.append({"PMID": i, "Source": "LitCovid", "Abstract": clean_abstract(abstract),
                                              "Categories": categories}, ignore_index=True)

                    # everything below is additional info/nice to have but not required
                    # override source if an explicit souce is provided in the litcovid jsons
                    if ("source" in json_doc.keys()):
                        meta_df.loc[meta_df["PMID"] == i, "Source"] = json_doc["source"]
                    if ("title" in json_doc.keys()):
                        meta_df.loc[meta_df["PMID"] == i, "Title"] = json_doc["title"]
                    if ("doi" in json_doc.keys()):
                        meta_df.loc[meta_df["PMID"] == i, "DOI"] = json_doc["doi"]
                    if ("date" in json_doc.keys()):
                        meta_df.loc[meta_df["PMID"] == i, "Date"] = json_doc["date"][:10]
                else:
                    abs_missing_or_short = abs_missing_or_short + 1
            else:
                abs_missing_or_short = abs_missing_or_short + 1

    print("A total of " + str(skipped) + " documents was skipped because of formatting issues")
    print(str(abs_missing_or_short) + " documents were left out because the abstract is missing or too short"
                                      " or because the categories were missing")
    print("New number of entries:", len(meta_df))

    # save the mappings
    meta_df.to_csv(LITCOVIDMAPPINGS, index=None)
    return meta_df

def missing_data_summary(df):
    percentage_missing = df.isnull().sum() * 100 / len(df)
    result = pd.DataFrame({"column_name": df.columns,
                           "percentage_missing": percentage_missing})
    print("Missing data")
    print(result)
    # print("Summary of the data")
    # print(df.describe())
    return result

if __name__ == "__main__":
    # adding some stop words manually
    MANUALFILTER = ["abstract", "background", "methods", "results", "conclusion", "copyright"]
    # download stop words and lemmatization wordnet
    nltk.download('stopwords')
    nltk.download('wordnet')

    # for the sake of simplicity and comparability, a fixed date is used
    # (otherwise new data would be downloaded each time the code is executed
    # and downloading the data is slow)
    DATE = "06082020"

    # (use this line to get the newest documents)
    # DATE = date.today().strftime("%m%d%Y")

    # abstracts shorter than 100 words get filtered out
    MINLEN = 100

    LITCOVIDMETA = "../data/litcovid_meta/" + \
                   DATE + ".litcovid.export.tsv"
    LITCOVIDMAPPINGS = "../data/litcovid_meta/litcovid_mappings.csv"

    litcovid_meta = litcovid_get_metadata(new=True)
    missing_data_summary(litcovid_meta)