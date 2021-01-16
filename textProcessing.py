import re
import sys
import inspect
from nltk.corpus import stopwords

class TextProcessing:
	def __init__(self, tokenPattern= r"([A-Za-z0-9]+)+"):
		'''
		Token pattern is passed into the constructor. The default token pattern is a sequence of alphanumeric
		characters, independent of capitalization (so Apple, apple, aPpLe are the same token).
		Runtime: O(1)
		'''
		self.__tokenPattern = tokenPattern
		self.__stopWords = stopwords.words('english')


	def generate_text(self, fh, block_limit=104857600):
		'''
		This is a generator that yields character sequence up to approximately 100 MB(chosen arbitrarily) at a time.
		In the case when a character sequence is very large, the block limit may get exceeded.
		Runtime:
		Linear runtime relative to input size where input size is proportional to block limit.
		'''
		block = []
		for line in fh:
			for word in line.split():
				block.append(word)
				if sys.getsizeof(block) >= block_limit:
					yield ' '.join(block)
					block = []

		# Yield the last block
		if block:
			yield ' '.join(block)


	def tokenize(self, TextFilePath):
		'''
		This method returns a list of unique tokens from a given file. The method - computeWordFrequencies
		written below is modified to be called by this method for better handling of very large files.

		Runtime:
		"generate_text()" runs linearly with respect to the file size.
		"re.findall()", "matches_lower", and "tokens.extend()" are computed linearly with respect to block size.
		Checking stopwords is done in polynomial time wrt to size of matches_lower and self.__stopWords.
		"computeWordFrequencies()"  has a linear runtime relative to number of tokens passed as its argument.
		This method has a Polynomial-runtime relative to input size where input size == file size.
		'''
		tokens = set()
		# Defining attribute here so that the same object for this
		# class can be used to tokenize multiple files.
		self.__tokensFrequency = {}

		try:
			with open(TextFilePath, 'r') as fh:
				for block in self.generate_text(fh):
					# Find matches in the string 
					matches = re.findall(self.__tokenPattern, block)
					# Convert matches to lower case
					matches_lower = [token.lower() for token in matches]
					new_tokens = []

					for match_lower in matches_lower:
						# Avoid stop words from being tokenized
						if not match_lower in self.__stopWords:
							new_tokens.append(match_lower)
					tokens = tokens.union(set(new_tokens))
					self.computeWordFrequencies(new_tokens)

		except Exception as e:
			print(e)
			raise SystemExit

		return list(tokens)


	def computeWordFrequencies(self, Token):
		'''
		This method counts the number of occurrences of each token in the token list.
		Runtime:
		Linear runtime relative to input size where input size is the number of tokens in the input list.
		'''

		# Get the caller method's name.
		curframe = inspect.currentframe()
		calframe = inspect.getouterframes(curframe, 2)
		if calframe[1][3] == "tokenize":
			# While tokenize() is running, this block of code runs to compute and store
			# token frequencies into self.__tokensFrequency attribute.
			# Doing this will prevent storing repeated tokens in the return list of tokenize
			# which may oterwise consume a lot of memory if we have a very large file.
			for token in Token:
				try:
					self.__tokensFrequency[token] += 1
				except KeyError:
					self.__tokensFrequency[token] = 1

		else:
			wordFrequencyDict = {}
			for token in Token:
				try:
					wordFrequencyDict[token] += 1
				except KeyError:
					wordFrequencyDict[token] = 1

			return wordFrequencyDict


	def print(self, Frequencies):
		'''
		This method prints the word frequency count onto the screen.
		The print out is ordered by decreasing frequency.
		Runtime:
		The for-loop executes n times where n == len(Frequencies).
		Runtime of "sorted" function is O(nlogn) where n == len(Frequencies).
		This method has O(nlogn) where n == len(Frequencies).
		'''
		for k,v in sorted(Frequencies.items(), key=lambda x: x[1], reverse=True):
			print(k, '->', v)


	def getWordFrequencies(self):
		'''
		Runtime: O(1)
		'''
		return self.__tokensFrequency 
		

if __name__ == "__main__":
	if len(sys.argv) != 2:
		print(f"Expected 1 argument(File Path) received {len(sys.argv)-1} arguments instead")
		raise SystemExit

	filePath = sys.argv[1]

	TextProcessor = TextProcessing()
	TextProcessor.tokenize(filePath)
	wordFrequencies = TextProcessor.getWordFrequencies()
	TextProcessor.print(wordFrequencies)