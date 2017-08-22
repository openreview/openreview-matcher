""" A script for training a w2v model using gensim """


import multiprocessing 
from gensim.models import Word2Vec
import os
import argparse


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

def train_w2v_model(location_of_training_documents, parameters, location_to_save):
	""" 
	Train skipgram w2v moodel using gensim "
	
	Parameters:
		@location_of_training_documents: a list of documents (strings)
		@parameters: a dict containing parameters for the w2v model
		@location_to_save: location to save the trained w2v model
	"""

	training_documents = get_all_training_documents(location_of_training_documents)	

	print("Num of training documents: {0}".format(len(training_documents)))

	print("Training skipgram w2v model...")
	model = Word2Vec(training_documents, sg=1, min_count=5, size=parameters['size'], window=parameters['window'],
                sample=parameters['sample'], negative=parameters['negative'], workers=parameters['workers'])

	print("Saving the model to {0}", location_to_save)
   	model.save(location_to_save)

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



if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-data", "--data", help="location of training documents", required=True)
	parser.add_argument("-size", "--size", help="size of the word embeddings", required=True)
	parser.add_argument("-window", "--window", help="window size", required=True)
	parser.add_argument("-save", "--save", help="location to save the w2v model", required=True)

	args = parser.parse_args()

	data_location = args.data
	embedding_size = int(args.size)
	window_size = int(args.window)
	save_location = args.save

	cores = multiprocessing.cpu_count()

	parameters = {"size": embedding_size, "window": window_size, "sample":1e-4, "negative":5, "workers":cores}
	train_w2v_model(data_location, parameters, save_location)




