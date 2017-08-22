""" Script that trains a phrase model on a corpora of documents """

from gensim.models import Phrases
import re
import os
import argparse

def tokenize_paper(paper):
    """ 
    Tokenizes a document
    
    Arguments:
          paper: a document represented by a string
          
    Returns:
            a list of tokens 
    """

    space_regexp = re.compile('[^a-zA-Z]')
    words = re.split(space_regexp, paper)
    words = filter(lambda x: len(x) > 0, words)
    words = [word.lower() for word in words]
    words = preprocess_documents.stop_word_removal(words)
    return words

def get_all_training_documents(data_location):	
	""" 
	Gathers all of the txt files from one location 
	into a list for training 
	
	Parameters:
		@data_location: location of training documents
	"""

	all_documents = [] 
	
	print("Getting all of the training documents from {0}".format(data_location))

	for idx, filename in enumerate(os.listdir(data_location), start=1):
		if filename.endswith(".txt"):
			with open(data_location + "/" + filename, "rb") as f:
				paper_content = tokenize_paper(" ".join(f.readlines())) 
				all_documents.append(" ".join(paper_content))

	print("Done getting all of the training documents...")

def export_phrases(documents, phrase_path, trigram_phrases_location):
	""" Export all phrases in the Phrase model to a txt file """	

	print("Exporting phrases to file...")

    phrase_model = Phrases.load(phrase_path)

    with open(trigram_phrases_location, "w") as f:
        for phrase, score in phrase_model.export_phrases(documents):
            f.write(u'{0}   {1} \n'.format(phrase, score))

def build_phrase_model(location_of_training_documents, location_to_save):
	""" Build a phrase model on a corpora of training documents """

	training_documents = get_all_training_documents(location_of_training_documents)

	print("Training on {0} documents...".format(len(training_documents)))

	print("Training Phrase Model...")

	bigram_model = Phrases(training_documents, min_count=5, threshold=10)
	trigram_model = Phrases(bigram_model[training_documents], min_count=5, threshold=10)
	trigram_model.save(location_to_save)
	# export_phrases(training_documents, location_to_save)
 


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-data", "--data", help="location of training documents")
	parser.add_argument("-save", "--save", help="location to save phrase model")

	args = parser.arg_parse()

	data_location = args.data	
	save_location = args.save

	build_phrase_model(data_location, save_location)

