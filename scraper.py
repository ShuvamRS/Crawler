import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from textProcessing import TextProcessing
import json
import requests
import time
import csv

PAGE_SIMILARITY_THRESHOLD = 0.9

# Low value page if number of tokens is less/more than threshold range.
TOKEN_COUNT_THRESHOLD = (50, 1000)

BASE_LINKS = {
    ".ics.uci.edu/",
    ".cs.uci.edu/",
    ".informatics.uci.edu/",
    ".stat.uci.edu/",
    "today.uci.edu/department/information_computer_sciences/"
}

def is_low_value(url, wordCount):
    sumTokenCount = len(wordCount)
    if sumTokenCount < TOKEN_COUNT_THRESHOLD[0] or sumTokenCount > TOKEN_COUNT_THRESHOLD[1]:
        print(f"{url} has low information value with # of tokens = {sumTokenCount}")
        return True
        
    return False


def is_unique_link(link):
    try:
        with open('pageContents/checked_urls.csv', 'r') as fh:
            reader = csv.reader(fh, delimiter='\n')
            prev_links = [data[0] for data in reader]

    except (FileNotFoundError, IndexError):
        prev_links = []

    for prev_link in prev_links:
        if link == prev_link:
            return False

    prev_links.append(link)

    with open('pageContents/checked_urls.csv','w') as fh:
        writer = csv.writer(fh, delimiter='\n')
        writer.writerow(prev_links)

    return True


def compute_near_duplicate_similarity(wordFreq_curPage, wordFreq_prevPages):
    curPage_set = set(wordFreq_curPage.keys())
    total_words_curPage = sum(wordFreq_curPage.values())
    similarity_score = {}

    for link in wordFreq_prevPages:
        wordFreq_prevPage = wordFreq_prevPages[link]
        num_similar_words = 0
        total_words_combined = total_words_curPage + sum(wordFreq_prevPage.values())

        prevPage_set = set(wordFreq_prevPage.keys())

        for word in curPage_set.intersection(prevPage_set):
            if wordFreq_prevPage[word] > wordFreq_curPage[word]: num_similar_words += wordFreq_curPage[word]
            else: num_similar_words += wordFreq_prevPage[word]

        # Compute union of word counts in two pages
        _union = total_words_combined - num_similar_words

        similarity_score[link] = num_similar_words / _union

    return similarity_score



def scraper(url, resp):
    try:
        page_content = resp.raw_response.content.decode('utf-8')
    except UnicodeDecodeError:
        return []
    except:
        print(f"Empty raw response for {url}")
        return []


    soup = BeautifulSoup(page_content, "html.parser")
    page_text = soup.get_text()

    if resp.status != 200 or page_text == "": return []

    # Write the text contents of page into pageContent.txt for tokenizing its contents
    with open("pageContents/pageContent.txt", 'w') as fh: fh.write(page_text)

    # Tokenize and get word frequencies from the page
    TextProcessor = TextProcessing()
    TextProcessor.tokenize("pageContents/pageContent.txt")
    cur_wordFrequencies = TextProcessor.getWordFrequencies()

    # Check if page has low information value
    if is_low_value(url, cur_wordFrequencies): return []

    # Load word frequencies from json file to check page similarity and append
    # to the file if similarity score is below a certain threshold.
    try:
        with open('pageContents/pageContent.json', 'r') as fh:
            prev_wordFrequencies = json.load(fh)
            similarityScores = compute_near_duplicate_similarity(cur_wordFrequencies, prev_wordFrequencies)
            for _url in similarityScores:
                if url != _url and similarityScores[_url] > PAGE_SIMILARITY_THRESHOLD:
                    print(f"\nContent in {url} is similar to {_url} with similarity score = {similarityScores[_url]}\n")
                    # avoid crawling similar pages
                    return list()

            prev_wordFrequencies[url] = cur_wordFrequencies
            with open('pageContents/pageContent.json', 'w') as fh:
                json.dump(prev_wordFrequencies, fh, indent=4)

    except (FileNotFoundError, json.decoder.JSONDecodeError):
        # Create a new file; there is no other page to check similarity with
        with open('pageContents/pageContent.json', 'w') as fh:
            json.dump({url: cur_wordFrequencies}, fh)

    return list(set([link for link in extract_next_links(url, resp) if is_valid(link) and is_unique_link(link)]))

def extract_next_links(url, resp):
    links = []

    page_content = resp.raw_response.content.decode('utf-8')
    soup = BeautifulSoup(page_content, "html.parser")
    parsed_url = urlparse(url)

    for anchor_tag in soup.findAll('a'):
        link = anchor_tag.get('href')
        # Defragment urls
        try: link = link.split("#")[0]
        except: continue

        if link != "" and link != None and re.match(r'^/\w+', link) != None:
            link = parsed_url.scheme + "://" + parsed_url.netloc + link

        links.append(link)

    return links


def is_valid(url):
    # Added ppsx
    match_pattern = r".*\.(css|js|bmp|gif|jpe?g|ico"\
    + r"|png|tiff?|mid|mp2|mp3|mp4"\
    + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"\
    + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"\
    + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"\
    + r"|epub|dll|cnf|tgz|sha1"\
    + r"|thmx|mso|arff|rtf|jar|csv"\
    + r"|rm|smil|wmv|swf|wma|zip|rar|gz"\
    + r"|ppsx)$"

    
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        # Checks whether url is within domains and paths given in BASE_LINKS
        contains_base_link = [base_link in url for base_link in BASE_LINKS]
        if not any(contains_base_link):
            return False

        # Validate query
        # Added replytocom=\d+ assuming that replies have low information value
        # Added version=\d+ and difftype=\w+ to avoid crawling pages with version-control/commit history.
        if re.match(r".*(replytocom=\d+|version=\d+|difftype=\w+)$", parsed.query.lower()) or re.match(match_pattern, parsed.query.lower()): return False

        # Validate path
        # return false if "pdf" is found in the path of the uri
        if re.match(r".+/pdf/.+", parsed.path.lower()): return False
        return not re.match(match_pattern, parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise